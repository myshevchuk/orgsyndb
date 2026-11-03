;;; orgsyndb-tests.el --- ERT tests for the orgsyndb package  -*- lexical-binding: t; -*-

;;; Commentary:

;; Run with:
;;
;;   emacs -Q --batch -l tests/el/orgsyndb-tests.el \
;;         -f ert-run-tests-batch-and-exit
;;
;; The suite loads the package from emacs/ relative to its own location
;; and works on temporary copies of tests/fixtures/collection/ and
;; examples/demo/.  It runs the repository's tools/orgsyndb for `index'
;; and `validate', and a stub program, which records its arguments and
;; hands every other subcommand to the real program, for the commands
;; that start servers, builds and PDFs.  No browser is started.  A test
;; that needs the Org export skips itself when ox-hugo is not cached.
;;
;; Each test names its scenario in its docstring.  In scenarios, the
;; character `¦' in a text marks where point goes.

;;; Code:

(require 'ert)
(require 'cl-lib)
(require 'subr-x)
(require 'iso8601)
;; The libraries the package builds on, loaded before it so that
;; "Loading changes nothing" sees only what the package itself does.
(require 'xref)
(require 'flymake)
(require 'eldoc)
(require 'time-stamp)
(require 'compile)
(require 'transient)
(require 'image)

(defconst orgsyndb-test-directory
  (file-name-directory (expand-file-name (or load-file-name
                                             buffer-file-name)))
  "The directory of this file.")

(defconst orgsyndb-test-repo
  (expand-file-name "../../" orgsyndb-test-directory)
  "The root of the repository, as a directory name.")

(defconst orgsyndb-test-program
  (expand-file-name "tools/orgsyndb" orgsyndb-test-repo)
  "The repository's program.")

(defconst orgsyndb-test-demo
  (expand-file-name "examples/demo/" orgsyndb-test-repo)
  "The demo collection.")

(defconst orgsyndb-test-collection
  (expand-file-name "tests/fixtures/collection/" orgsyndb-test-repo)
  "The test collection.")

(defconst orgsyndb-test-fixtures
  (expand-file-name "tests/fixtures/" orgsyndb-test-repo)
  "The fixtures directory.")

(defconst orgsyndb-test-wrong-weekday
  (expand-file-name "org-invalid/wrong-weekday/org/OSDB-0206-wrong-weekday.org"
                    orgsyndb-test-fixtures)
  "An Org source whose `#+CREATED' names the wrong weekday.")

(defconst orgsyndb-test-watched
  '(before-save-hook after-save-hook completion-at-point-functions
                     xref-backend-functions flymake-diagnostic-functions
                     eldoc-documentation-functions time-stamp-format)
  "The global values that loading the package must leave alone.")

(defconst orgsyndb-test-before-load
  (mapcar (lambda (variable)
            (cons variable (and (boundp variable)
                                (copy-tree (default-value variable)))))
          orgsyndb-test-watched)
  "The values of `orgsyndb-test-watched' before the package loaded.")

(defvar orgsyndb-test-load-error nil
  "The error that loading the package signalled, or nil.")

(add-to-list 'load-path (expand-file-name "emacs" orgsyndb-test-repo))
(condition-case err
    (require 'orgsyndb)
  (error (setq orgsyndb-test-load-error err)))

(defconst orgsyndb-test-after-load
  (mapcar (lambda (variable)
            (cons variable (and (boundp variable)
                                (copy-tree (default-value variable)))))
          orgsyndb-test-watched)
  "The values of `orgsyndb-test-watched' just after the package loaded.")

(defvar orgsyndb-test-mode-after-load (bound-and-true-p global-orgsyndb-mode)
  "Whether `global-orgsyndb-mode' was on just after the package loaded.")

(defvar orgsyndb-test-org-after-load (featurep 'org)
  "Whether Org was loaded just after the package loaded.")

(defun orgsyndb-test-require ()
  "Fail the current test when the package did not load."
  (when orgsyndb-test-load-error
    (ert-fail (list "the package did not load" orgsyndb-test-load-error))))

;;;; Collections, buffers and processes

(defvar orgsyndb-test-bases nil
  "The temporary directories of the current test.")

(defun orgsyndb-test-temp-directory ()
  "Return a new temporary directory, removed when the test ends."
  (let ((base (file-name-as-directory (make-temp-file "orgsyndb test " t))))
    (push base orgsyndb-test-bases)
    base))

(defun orgsyndb-test-copy (source)
  "Copy the collection SOURCE, without its generated directories.
Return the copy as a directory name."
  (let ((root (file-name-as-directory
               (expand-file-name "collection copy"
                                 (orgsyndb-test-temp-directory)))))
    (copy-directory source root nil nil t)
    (dolist (name '("build" "public" "pdf"))
      (let ((directory (expand-file-name name root)))
        (when (file-directory-p directory)
          (delete-directory directory t))))
    root))

(defun orgsyndb-test-processes ()
  "Return the live processes the package started."
  (cl-remove-if-not (lambda (process)
                      (and (process-get process 'orgsyndb)
                           (process-live-p process)))
                    (process-list)))

(defun orgsyndb-test-wait (predicate &optional seconds)
  "Wait until PREDICATE returns non-nil, at most SECONDS (default 60).
Fail the test when it does not."
  (let ((deadline (+ (float-time) (or seconds 60))))
    (while (and (not (funcall predicate)) (< (float-time) deadline))
      (accept-process-output nil 0.05))
    (should (funcall predicate))))

(defun orgsyndb-test-settle ()
  "Wait until no process of the package runs, then wait a moment more."
  (orgsyndb-test-wait (lambda () (null (orgsyndb-test-processes))) 120)
  (accept-process-output nil 0.1))

(defun orgsyndb-test-cleanup ()
  "Stop the package's processes, kill the test's buffers, remove its
directories and turn the global mode off."
  (dolist (process (orgsyndb-test-processes))
    (delete-process process))
  (dolist (buffer (buffer-list))
    (let ((file (buffer-file-name buffer)))
      (when (or (and file (cl-some (lambda (base)
                                     (string-prefix-p base file))
                                   orgsyndb-test-bases))
                (string-prefix-p "*orgsyndb" (buffer-name buffer)))
        (with-current-buffer buffer
          (set-buffer-modified-p nil))
        (kill-buffer buffer))))
  (dolist (base orgsyndb-test-bases)
    (delete-directory base t))
  (setq orgsyndb-test-bases nil)
  (global-orgsyndb-mode -1))

(defmacro orgsyndb-test-with (spec &rest body)
  "Run BODY with a copy of a collection; SPEC is (VAR SOURCE).
VAR holds the copy.  `global-orgsyndb-mode' is on, the program is the
repository's, and validation on save and diagnostics are off."
  (declare (indent 1))
  `(let ((orgsyndb-program orgsyndb-test-program)
         (orgsyndb-validate-on-save nil)
         (orgsyndb-diagnostics nil)
         (orgsyndb-update-timestamps t)
         (orgsyndb-preview-port 8000))
     (orgsyndb-test-require)
     (unwind-protect
         (let ((,(car spec) (orgsyndb-test-copy ,(cadr spec))))
           (global-orgsyndb-mode 1)
           ,@body)
       (orgsyndb-test-cleanup))))

(defun orgsyndb-test-visit (root file)
  "Visit FILE of the collection ROOT and return its buffer."
  (find-file-noselect (expand-file-name file root)))

(defun orgsyndb-test-write (root file text)
  "Write TEXT to FILE of the collection ROOT."
  (let ((path (expand-file-name file root)))
    (make-directory (file-name-directory path) t)
    (with-temp-file path
      (insert text))))

(defun orgsyndb-test-mark ()
  "Remove the first `¦' of the buffer and put point where it was."
  (goto-char (point-min))
  (search-forward "¦")
  (delete-char -1))

(defun orgsyndb-test-put (old new)
  "Replace the first OLD in the buffer with NEW, then `orgsyndb-test-mark'."
  (goto-char (point-min))
  (search-forward old)
  (replace-match new t t)
  (orgsyndb-test-mark))

(defun orgsyndb-test-put-line (prefix new)
  "Replace the first line beginning with PREFIX with NEW, then mark."
  (goto-char (point-min))
  (re-search-forward (concat "^" (regexp-quote prefix) ".*$"))
  (replace-match new t t)
  (orgsyndb-test-mark))

(defun orgsyndb-test-complete ()
  "Call `orgsyndb-completion-at-point' at point.
Return nil when it returns nil, and otherwise (COMPLETIONS . PROPS):
the completions of its table for the text from its start to point, and
its properties."
  (pcase (orgsyndb-completion-at-point)
    ('nil nil)
    (`(,start ,_end ,table . ,props)
     (cons (all-completions (buffer-substring-no-properties start (point))
                            table)
           props))))

(defun orgsyndb-test-annotation (result candidate)
  "Return the annotation that the completion RESULT gives CANDIDATE."
  (funcall (plist-get (cdr result) :annotation-function) candidate))

(defun orgsyndb-test-messages ()
  "Return the text of the *Messages* buffer."
  (with-current-buffer (messages-buffer)
    (buffer-string)))

(defun orgsyndb-test-last-message ()
  "Return the last line of the *Messages* buffer."
  (car (last (split-string (string-trim-right (orgsyndb-test-messages))
                           "\n"))))

(defun orgsyndb-test-line-of (buffer text)
  "Return the line of BUFFER that holds TEXT first."
  (with-current-buffer buffer
    (save-excursion
      (goto-char (point-min))
      (search-forward text)
      (line-number-at-pos))))

(defun orgsyndb-test-buffer-line (buffer number)
  "Return line NUMBER of BUFFER."
  (with-current-buffer buffer
    (save-excursion
      (goto-char (point-min))
      (forward-line (1- number))
      (buffer-substring-no-properties (line-beginning-position)
                                      (line-end-position)))))

(defun orgsyndb-test-file-line (file prefix)
  "Return the first line of FILE that begins with PREFIX."
  (with-temp-buffer
    (insert-file-contents file)
    (goto-char (point-min))
    (re-search-forward (concat "^" (regexp-quote prefix) ".*$"))
    (match-string 0)))

(defun orgsyndb-test-diagnostics (buffer)
  "Return what `orgsyndb-flymake' reports in BUFFER, as a list of
\(LINE TYPE TEXT)."
  (with-current-buffer buffer
    (let (reported)
      (orgsyndb-flymake (lambda (diagnostics &rest _)
                          (setq reported diagnostics)))
      (mapcar (lambda (diagnostic)
                (list (line-number-at-pos (flymake-diagnostic-beg diagnostic))
                      (flymake-diagnostic-type diagnostic)
                      (flymake-diagnostic-text diagnostic)))
              reported))))

(defun orgsyndb-test-ox-hugo ()
  "Skip the current test unless ox-hugo is cached."
  (unless (file-directory-p
           (expand-file-name ".emacs-batch/elpa/ox-hugo/" orgsyndb-test-repo))
    (ert-skip "ox-hugo is not cached in .emacs-batch/elpa/ox-hugo/")))

(defun orgsyndb-test-collection-name (root)
  "Return ROOT as the program receives it after `-C'."
  (directory-file-name root))

;;;; The stub program

(defun orgsyndb-test-stub (cases)
  "Write a stub program and return its file name.
The stub appends `begin SUBCOMMAND', one `arg A' line per argument
and, when it returns, `end SUBCOMMAND' to `stub.log' beside it.  CASES
are `case' arms of sh run on the subcommand, with $2 the collection; a
subcommand no arm names runs the repository's program."
  (let* ((directory (orgsyndb-test-temp-directory))
         (file (expand-file-name "orgsyndb stub" directory)))
    (with-temp-file file
      (insert "#!/bin/sh\n"
              "log=\"$(dirname \"$0\")/stub.log\"\n"
              "sub=\"$3\"\n"
              "echo \"begin $sub\" >> \"$log\"\n"
              "for a in \"$@\"; do echo \"arg $a\" >> \"$log\"; done\n"
              "case \"$sub\" in\n"
              cases
              "  *) exec " (shell-quote-argument orgsyndb-test-program)
              " \"$@\";;\n"
              "esac\n"
              "status=$?\n"
              "echo \"end $sub\" >> \"$log\"\n"
              "exit $status\n"))
    (set-file-modes file #o755)
    file))

(defun orgsyndb-test-stub-log (stub)
  "Return the lines that STUB logged."
  (let ((log (expand-file-name "stub.log" (file-name-directory stub))))
    (when (file-exists-p log)
      (with-temp-buffer
        (insert-file-contents log)
        (split-string (buffer-string) "\n" t)))))

(defun orgsyndb-test-stub-calls (stub)
  "Return the argument lists STUB received, in order."
  (let (calls)
    (dolist (line (orgsyndb-test-stub-log stub))
      (cond ((string-prefix-p "begin " line) (push nil calls))
            ((string-prefix-p "arg " line)
             (push (substring line 4) (car calls)))))
    (nreverse (mapcar #'reverse calls))))

(defun orgsyndb-test-stub-events (stub subcommands)
  "Return STUB's `begin' and `end' lines for SUBCOMMANDS, in order."
  (cl-remove-if-not
   (lambda (line)
     (and (string-match "\\`\\(?:begin\\|end\\) \\(.*\\)\\'" line)
          (member (match-string 1 line) subcommands)))
   (orgsyndb-test-stub-log stub)))

(defmacro orgsyndb-test-at (time &rest body)
  "Run BODY with the current time fixed at the ISO 8601 TIME."
  (declare (indent 1))
  (let ((fixed (make-symbol "fixed"))
        (stamp (make-symbol "stamp")))
    `(let ((,fixed (encode-time (iso8601-parse ,time)))
           (,stamp (symbol-function 'time-stamp-string)))
       (cl-letf (((symbol-function 'orgsyndb--now) (lambda () ,fixed))
                 ((symbol-function 'time-stamp-string)
                  (lambda (&optional format _time)
                    (funcall ,stamp format ,fixed))))
         ,@body))))

(defmacro orgsyndb-test-answering (answers &rest body)
  "Run BODY with the minibuffer reading functions returning ANSWERS.
`read-string', `completing-read', `read-number', `y-or-n-p' and
`completing-read-multiple' each take the next answer, a string; a
number is read from it, a yes-or-no answer is `y' or `n', and a
multiple answer is split at commas."
  (declare (indent 1))
  (let ((queue (make-symbol "queue")))
    `(let ((,queue (copy-sequence ,answers)))
       (cl-letf (((symbol-function 'read-string)
                  (lambda (&rest _) (pop ,queue)))
                 ((symbol-function 'completing-read)
                  (lambda (&rest _) (pop ,queue)))
                 ((symbol-function 'read-number)
                  (lambda (&rest _) (string-to-number (pop ,queue))))
                 ((symbol-function 'y-or-n-p)
                  (lambda (&rest _) (equal (pop ,queue) "y")))
                 ((symbol-function 'completing-read-multiple)
                  (lambda (&rest _) (split-string (pop ,queue) "," t))))
         ,@body
         (should (null ,queue))))))

;;;; Package files and the program

(ert-deftest orgsyndb-test-loading-changes-nothing ()
  "Scenario: Loading changes nothing."
  (orgsyndb-test-require)
  (should (equal orgsyndb-test-after-load orgsyndb-test-before-load))
  (should-not orgsyndb-test-mode-after-load)
  (should-not orgsyndb-test-org-after-load))

(ert-deftest orgsyndb-test-program-beside-the-package ()
  "Scenario: Program beside the package."
  (orgsyndb-test-require)
  (should (equal (eval (car (get 'orgsyndb-program 'standard-value)) t)
                 orgsyndb-test-program)))

;;;; Turning the mode on

(ert-deftest orgsyndb-test-kinds ()
  "Scenario: Kinds."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (should (equal
             (mapcar (lambda (file)
                       (orgsyndb-file-kind (expand-file-name file root)))
                     '("org/procedures/OSDB-0007-ethyl-cinnamate.de.org"
                       "md/procedures/OSDB-0002-aspirin.md"
                       "md/sequences/SEQ-0001-aspirin-from-wintergreen.md"
                       "compounds/acetone.toml"
                       "vocabularies/projects.toml"
                       "orgsyndb.toml"
                       "build/export/OSDB-0007-ethyl-cinnamate.md"
                       "static/structures/isopentyl-acetate.svg"))
             '(org-procedure md-procedure sequence compound vocabulary
                             settings nil nil)))
    (should (equal (orgsyndb-collection-root
                    (expand-file-name "compounds/acetone.toml" root))
                   root))))

(ert-deftest orgsyndb-test-turned-on-by-visiting ()
  "Scenario: Turned on by visiting."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (let* ((outside (orgsyndb-test-temp-directory))
           (other (progn (orgsyndb-test-write outside "notes.md" "# Notes\n")
                         (find-file-noselect
                          (expand-file-name "notes.md" outside)))))
      (should (buffer-local-value
               'orgsyndb-mode
               (orgsyndb-test-visit root
                                    "md/procedures/OSDB-0002-aspirin.md")))
      (should-not (buffer-local-value 'orgsyndb-mode other)))))

;;;; Collection data

(ert-deftest orgsyndb-test-index-on-first-use ()
  "Scenario: First use."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (with-current-buffer (orgsyndb-test-visit
                          root "md/procedures/OSDB-0002-aspirin.md")
      (let ((index (orgsyndb-index)))
        (should (= (length (alist-get 'compounds index)) 20))
        (should (equal (alist-get 'site_language index)
                       (alist-get 'site_language (orgsyndb-index root))))))))

(ert-deftest orgsyndb-test-refresh-after-a-save ()
  "Scenario: Refresh after a save."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (orgsyndb-index root)
    (with-current-buffer (orgsyndb-test-visit root "compounds/ethanol.toml")
      (should orgsyndb-mode)
      (insert "name = \"Ethanol\"\nformula = \"C2H6O\"\nmw = 46.07\n"
              "smiles = \"CCO\"\n")
      (save-buffer))
    (orgsyndb-test-wait
     (lambda ()
       (cl-find "ethanol" (alist-get 'compounds (orgsyndb-index root))
                :key (lambda (entry) (alist-get 'key entry))
                :test #'equal)))
    (orgsyndb-test-settle)))

(ert-deftest orgsyndb-test-new-org-source-after-a-save ()
  "Scenario: A new Org source after a save."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (orgsyndb-index root)
    (with-current-buffer (orgsyndb-test-visit
                          root "org/procedures/OSDB-0010-test.org")
      (should orgsyndb-mode)
      (insert "#+TITLE: Test\n")
      (save-buffer))
    (orgsyndb-test-wait
     (lambda ()
       (cl-find "org/procedures/OSDB-0010-test.org" (orgsyndb-procedures root)
                :key (lambda (record) (alist-get 'path record))
                :test #'equal)))
    (orgsyndb-test-settle)))

(ert-deftest orgsyndb-test-a-failed-run-keeps-the-index ()
  "Scenario: A failed run keeps the index."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (with-current-buffer (orgsyndb-test-visit root "orgsyndb.toml")
      (let ((index (orgsyndb-index))
            (orgsyndb-program
             (orgsyndb-test-stub "  index) echo boom >&2; exit 1;;\n")))
        (orgsyndb-refresh-index)
        (should (eq (orgsyndb-index) index))
        (should (string-match-p "boom" (orgsyndb-test-last-message)))))))

(ert-deftest orgsyndb-test-org-records ()
  "Scenario: Org records."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (let* ((record (cl-find "org/procedures/OSDB-0007-ethyl-cinnamate.org"
                            (orgsyndb-procedures root)
                            :key (lambda (record) (alist-get 'path record))
                            :test #'equal))
           (front-matter (alist-get 'front_matter record)))
      (should (equal (alist-get 'title front-matter) "Ethyl cinnamate"))
      (should (equal (alist-get 'status front-matter) "draft")))))

;;;; Completion in Markdown procedures

(defmacro orgsyndb-test-in-aspirin (spec &rest body)
  "Run BODY in a buffer visiting OSDB-0002-aspirin.md of a copy of the
test collection; SPEC is (ROOT), the variable that holds the copy."
  (declare (indent 1))
  `(orgsyndb-test-with (,(car spec) orgsyndb-test-collection)
     (with-current-buffer (orgsyndb-test-visit
                           ,(car spec) "md/procedures/OSDB-0002-aspirin.md")
       ,@body)))

(ert-deftest orgsyndb-test-complete-status ()
  "Scenario: Status."
  (orgsyndb-test-in-aspirin (_root)
    (orgsyndb-test-put "status = \"draft\"" "status = \"d¦\"")
    (should (equal (car (orgsyndb-test-complete)) '("draft")))))

(ert-deftest orgsyndb-test-complete-reaction-type ()
  "Scenario: Reaction type."
  (orgsyndb-test-in-aspirin (_root)
    (orgsyndb-test-put "reaction_types = [\"acylation\"]"
                       "reaction_types = [\"est¦\"]")
    (let ((result (orgsyndb-test-complete)))
      (should (equal (car result) '("esterification")))
      (should (string-match-p "Esterification"
                              (orgsyndb-test-annotation result
                                                        "esterification"))))))

(ert-deftest orgsyndb-test-complete-compound-of-a-product ()
  "Scenario: Compound of a product."
  (orgsyndb-test-in-aspirin (_root)
    (orgsyndb-test-put-line
     "products = "
     "products = [{ compound = \"acetyls¦\", yield_percent = 75 }]")
    (let ((result (orgsyndb-test-complete)))
      (should (equal (car result) '("acetylsalicylic-acid")))
      (should (string-match-p "Acetylsalicylic acid"
                              (orgsyndb-test-annotation
                               result "acetylsalicylic-acid"))))))

(ert-deftest orgsyndb-test-complete-declared-choice ()
  "Scenario: Declared choice."
  (orgsyndb-test-in-aspirin (_root)
    (orgsyndb-test-put-line "project = " "project = \"first¦\"")
    (let ((result (orgsyndb-test-complete)))
      (should (equal (car result) '("first-year-practical")))
      (should (string-match-p "Teaching › First-year practical"
                              (orgsyndb-test-annotation
                               result "first-year-practical"))))))

(ert-deftest orgsyndb-test-complete-keys-not-yet-set ()
  "Scenario: Keys not yet set."
  (orgsyndb-test-in-aspirin (_root)
    (goto-char (point-min))
    (forward-line 1)
    (re-search-forward "^\\+\\+\\+$")
    (goto-char (match-beginning 0))
    (insert "sc¦\n")
    (orgsyndb-test-mark)
    (should (equal (sort (car (orgsyndb-test-complete)) #'string<)
                   '("scheme_image" "scope")))))

(ert-deftest orgsyndb-test-complete-nothing-in-the-body ()
  "Scenario: Nothing in the body."
  (orgsyndb-test-in-aspirin (_root)
    (goto-char (point-min))
    (re-search-forward "^## Summary\n")
    (forward-char 3)
    (should-not (orgsyndb-completion-at-point))))

;;;; Completion in Org procedures

(defconst orgsyndb-test-org-header
  (concat "#+TITLE: Test\n"
          "#+CREATED: [2026-10-20 Tue 09:58:17]\n"
          "#+LAST_MODIFIED: [2026-10-20 Tue 10:22:50]\n"
          "#+HUGO_SLUG: osdb-0010\n"
          "#+HUGO_TAGS: sample-data\n"
          "#+HUGO_CUSTOM_FRONT_MATTER: :id \"OSDB-0010\"\n"
          "#+HUGO_CUSTOM_FRONT_MATTER: :status \"draft\"\n")
  "The header of the Org source of the Org completion scenarios.")

(defun orgsyndb-test-org-complete (root lines)
  "Write OSDB-0010-test.org into ROOT, its header followed by LINES and
a Summary, visit it, put point at its mark and complete."
  (orgsyndb-test-write root "org/procedures/OSDB-0010-test.org"
                       (concat orgsyndb-test-org-header lines
                               "\n* Summary\nA test.\n"))
  (with-current-buffer (orgsyndb-test-visit
                        root "org/procedures/OSDB-0010-test.org")
    (orgsyndb-test-mark)
    (orgsyndb-test-complete)))

(ert-deftest orgsyndb-test-complete-custom-front-matter-keys ()
  "Scenario: Custom front-matter keys."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (let ((completions (car (orgsyndb-test-org-complete
                             root "#+HUGO_CUSTOM_FRONT_MATTER: :s¦\n"))))
      (dolist (key '(":scale" ":substrates" ":scheme_image"))
        (should (member key completions)))
      (dolist (key '(":status" ":scope"))
        (should-not (member key completions))))))

(ert-deftest orgsyndb-test-complete-reaction-type-in-a-list ()
  "Scenario: Reaction type in a list."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (should (equal (car (orgsyndb-test-org-complete
                         root (concat "#+HUGO_CUSTOM_FRONT_MATTER: "
                                      ":reaction_types '(\"ol¦\")\n")))
                   '("olefination")))))

(ert-deftest orgsyndb-test-complete-product-compound ()
  "Scenario: Product compound."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (should (equal (car (orgsyndb-test-org-complete
                         root (concat "#+HUGO_CUSTOM_FRONT_MATTER: :products "
                                      "'(((compound . \"ethyl-c¦\") "
                                      "(yield_percent . 80)))\n")))
                   '("ethyl-cinnamate")))))

(ert-deftest orgsyndb-test-complete-tags ()
  "Scenario: Tags."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (orgsyndb-test-write root "org/procedures/OSDB-0010-test.org"
                         (concat (string-replace
                                  "#+HUGO_TAGS: sample-data\n"
                                  "#+HUGO_TAGS: sample-data wit¦\n"
                                  orgsyndb-test-org-header)
                                 "\n* Summary\nA test.\n"))
    (with-current-buffer (orgsyndb-test-visit
                          root "org/procedures/OSDB-0010-test.org")
      (orgsyndb-test-mark)
      (should (equal (car (orgsyndb-test-complete)) '("wittig"))))))

(ert-deftest orgsyndb-test-complete-scope-table-cell ()
  "Scenario: Scope table cell."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (should (equal (car (orgsyndb-test-org-complete
                         root (concat "\n#+NAME: scope\n"
                                      "| substrates | products "
                                      "| yield_percent |\n"
                                      "|---+---+---|\n"
                                      "| aceto¦ | | |\n")))
                   '("acetone" "acetophenone")))))

;;;; Completion in sequences and compound files

(ert-deftest orgsyndb-test-complete-step-procedure ()
  "Scenario: Step procedure."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (with-current-buffer (orgsyndb-test-visit
                          root
                          "md/sequences/SEQ-0001-aspirin-from-wintergreen.md")
      (orgsyndb-test-put-line "steps = "
                              "steps = [{ procedure = \"OSDB-000¦\" }]")
      (let ((result (orgsyndb-test-complete)))
        (should (equal (sort (car result) #'string<)
                       (mapcar (lambda (n) (format "OSDB-%04d" n))
                               (number-sequence 1 9))))
        (should (string-match-p "Ethyl cinnamate"
                                (orgsyndb-test-annotation result
                                                          "OSDB-0007")))))))

(ert-deftest orgsyndb-test-complete-step-entry ()
  "Scenario: Step entry."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (with-current-buffer (orgsyndb-test-visit
                          root
                          "md/sequences/SEQ-0001-aspirin-from-wintergreen.md")
      (orgsyndb-test-put-line
       "steps = " "steps = [{ procedure = \"OSDB-0009\", entry = ¦}]")
      (let ((result (orgsyndb-test-complete)))
        (should (equal (car result) '("1" "2" "3")))
        (should (string-match-p "1-biphenyl-4-yl-ethanol"
                                (orgsyndb-test-annotation result "1")))))))

(ert-deftest orgsyndb-test-complete-step-entry-of-an-org-general-procedure ()
  "Scenario: Step entry of an Org general procedure."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (copy-file (expand-file-name "export/OSDB-0909-scope-table.org"
                                 orgsyndb-test-fixtures)
               (expand-file-name "org/procedures/" root))
    (with-current-buffer (orgsyndb-test-visit
                          root
                          "md/sequences/SEQ-0001-aspirin-from-wintergreen.md")
      (orgsyndb-test-put-line
       "steps = " "steps = [{ procedure = \"OSDB-0909\", entry = ¦}]")
      (let* ((result (orgsyndb-test-complete))
             (annotation (orgsyndb-test-annotation result "1")))
        (should (equal (car result) '("1" "2" "3")))
        (should (string-match-p "ethyl-acetate" annotation))
        (should (string-match-p "propyl-acetate" annotation))))))

(ert-deftest orgsyndb-test-complete-compound-file ()
  "Scenario: Compound file."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (orgsyndb-test-write root "compounds/test.toml"
                         "name = \"Test\"\nchem¦\ngroup = \"fin\"\n")
    (with-current-buffer (orgsyndb-test-visit root "compounds/test.toml")
      (orgsyndb-test-mark)
      (should (equal (car (orgsyndb-test-complete)) '("chemical_class")))
      (goto-char (point-min))
      (search-forward "\"fin")
      (should (equal (car (orgsyndb-test-complete)) '("final-products"))))))

;;;; Inserting a compound

(ert-deftest orgsyndb-test-insert-by-name ()
  "Scenario: Insert by name."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (with-current-buffer (orgsyndb-test-visit
                          root "md/procedures/OSDB-0002-aspirin.de.md")
      (goto-char (point-max))
      (let (offered)
        (cl-letf (((symbol-function 'completing-read)
                   (lambda (_prompt collection &rest _)
                     (setq offered (all-completions "" collection))
                     "Essigsäureanhydrid (acetic-anhydride)")))
          (orgsyndb-insert-compound))
        (should (member "Essigsäureanhydrid (acetic-anhydride)" offered)))
      (should (equal (buffer-substring-no-properties
                      (- (point) (length "acetic-anhydride")) (point))
                     "acetic-anhydride")))))

;;;; Definitions and references

(defun orgsyndb-test-definitions ()
  "Return the files and lines of the definitions of the identifier at
point, as a list of (FILE . LINE)."
  (let ((backend (xref-find-backend)))
    (should (eq backend 'orgsyndb))
    (mapcar (lambda (item)
              (let ((location (xref-item-location item)))
                (cons (xref-location-group location)
                      (xref-location-line location))))
            (xref-backend-definitions
             backend (xref-backend-identifier-at-point backend)))))

(ert-deftest orgsyndb-test-compound-definition ()
  "Scenario: Compound definition."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (with-current-buffer (orgsyndb-test-visit
                          root "md/procedures/OSDB-0002-aspirin.md")
      (goto-char (point-min))
      (search-forward "\"acetic-anh")
      (should (equal (orgsyndb-test-definitions)
                     (list (cons (expand-file-name
                                  "compounds/acetic-anhydride.toml" root)
                                 1)))))))

(ert-deftest orgsyndb-test-procedure-definition-in-the-readers-language ()
  "Scenario: Procedure definition in the reader's language."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (pcase-dolist (`(,sequence . ,procedure)
                   '(("SEQ-0001-aspirin-from-wintergreen.md"
                      . "OSDB-0001-salicylic-acid.org")
                     ("SEQ-0001-aspirin-from-wintergreen.de.md"
                      . "OSDB-0001-salicylic-acid.de.org")))
      (with-current-buffer (orgsyndb-test-visit
                            root (concat "md/sequences/" sequence))
        (goto-char (point-min))
        (search-forward "\"OSDB-00")
        (should (equal (mapcar #'car (orgsyndb-test-definitions))
                       (list (expand-file-name
                              (concat "org/procedures/" procedure)
                              root))))))))

(ert-deftest orgsyndb-test-compound-references ()
  "Scenario: Compound references."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (with-current-buffer (orgsyndb-test-visit root "orgsyndb.toml")
      (let ((files (delete-dups
                    (mapcar (lambda (item)
                              (xref-location-group (xref-item-location item)))
                            (xref-backend-references 'orgsyndb
                                                     "acetic-anhydride")))))
        (should (member (expand-file-name "md/procedures/OSDB-0002-aspirin.md"
                                          root)
                        files))
        (should (member (expand-file-name
                         "md/procedures/OSDB-0002-aspirin.de.md" root)
                        files))
        (should-not (member (expand-file-name
                             "compounds/acetic-anhydride.toml" root)
                            files))))))

;;;; Documentation at point

(ert-deftest orgsyndb-test-eldoc-compound-at-point ()
  "Scenario: Compound at point."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (with-current-buffer (orgsyndb-test-visit
                          root "md/procedures/OSDB-0002-aspirin.md")
      (goto-char (point-min))
      (search-forward "\"acetic-anh")
      (should (equal (orgsyndb-eldoc #'ignore)
                     (concat "acetic-anhydride: Acetic anhydride · C4H6O3 · "
                             "102.09 g/mol · CAS 108-24-7"))))))

(ert-deftest orgsyndb-test-eldoc-procedure-at-point ()
  "Scenario: Procedure at point."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (with-current-buffer (orgsyndb-test-visit
                          root "md/sequences/SEQ-0002-biphenylyl-ethanol.md")
      (goto-char (point-min))
      (search-forward "\"OSDB-00")
      (should (equal (orgsyndb-eldoc #'ignore)
                     "OSDB-0004 4-Acetylbiphenyl · draft")))))

;;;; Language variants

(defun orgsyndb-test-headings (text regexp)
  "Return the matches of group 1 of REGEXP in TEXT, in order."
  (let (found (start 0))
    (while (string-match regexp text start)
      (push (match-string 1 text) found)
      (setq start (match-end 0)))
    (nreverse found)))

(defun orgsyndb-test-file-text (file)
  "Return the contents of FILE."
  (with-temp-buffer
    (insert-file-contents file)
    (buffer-string)))

(defconst orgsyndb-test-german-sections
  '("Zusammenfassung" "Reagenzien" "Durchführung"
    "Aufarbeitung und Reinigung" "Charakterisierung" "Anmerkungen"
    "Gefahren und Entsorgung" "Literatur")
  "The German section names in order.")

(defconst orgsyndb-test-section-text "\\(\\(?:[^*\n].*\n\\|\n\\)*\\)"
  "The text of an Org section up to the next heading, as group 1.")

(ert-deftest orgsyndb-test-org-translation ()
  "Scenario: Org translation."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (let ((german (expand-file-name
                   "org/procedures/OSDB-0007-ethyl-cinnamate.de.org" root))
          (source (expand-file-name
                   "org/procedures/OSDB-0007-ethyl-cinnamate.org" root)))
      (delete-file german)
      (with-current-buffer (find-file-noselect source)
        (orgsyndb-test-at "2026-07-15T10:00:00Z"
          (orgsyndb-create-translation)))
      (should (file-exists-p german))
      (let ((text (orgsyndb-test-file-text german))
            (original (orgsyndb-test-file-text source)))
        (should (equal (orgsyndb-test-headings
                        text "^\\(#\\+HUGO_CUSTOM_FRONT_MATTER:.*\\)$")
                       (orgsyndb-test-headings
                        original "^\\(#\\+HUGO_CUSTOM_FRONT_MATTER:.*\\)$")))
        (should (string-match-p
                 "^#\\+CREATED: \\[2026-07-15 Wed 12:00:00\\]$" text))
        (should (string-match-p
                 "^#\\+LAST_MODIFIED: \\[2026-07-15 Wed 12:00:00\\]$" text))
        (should (equal (orgsyndb-test-headings text "^\\* \\(.*\\)$")
                       orgsyndb-test-german-sections))
        (should (equal (orgsyndb-test-headings
                        text (concat "^\\* Zusammenfassung\n"
                                     orgsyndb-test-section-text))
                       (orgsyndb-test-headings
                        original (concat "^\\* Summary\n"
                                         orgsyndb-test-section-text))))
        (should (null (car (osdb-org-lint text))))
        (should (equal (buffer-file-name (window-buffer (selected-window)))
                       german))))))

(ert-deftest orgsyndb-test-markdown-translation ()
  "Scenario: Markdown translation."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (let ((german (expand-file-name "md/procedures/OSDB-0002-aspirin.de.md"
                                    root))
          (source (expand-file-name "md/procedures/OSDB-0002-aspirin.md"
                                    root)))
      (delete-file german)
      (with-current-buffer (find-file-noselect source)
        (orgsyndb-test-at "2026-01-15T10:00:00Z"
          (orgsyndb-create-translation)))
      (let* ((text (orgsyndb-test-file-text german))
             (original (orgsyndb-test-file-text source))
             (front (lambda (text)
                      (cl-remove-if
                       (lambda (line)
                         (string-match-p "\\`\\(?:date\\|lastmod\\) =" line))
                       (split-string (car (split-string
                                           (substring text 4) "^\\+\\+\\+$"))
                                     "\n")))))
        (should (string-match-p "^date = 2026-01-15T11:00:00\\+01:00$" text))
        (should (string-match-p "^lastmod = 2026-01-15T11:00:00\\+01:00$"
                                text))
        (should (equal (orgsyndb-test-headings text "^## \\(.*\\)$")
                       orgsyndb-test-german-sections))
        (should (equal (funcall front text) (funcall front original)))))))

(ert-deftest orgsyndb-test-existing-translation ()
  "Scenario: Existing translation."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (let* ((german (expand-file-name
                    "org/procedures/OSDB-0007-ethyl-cinnamate.de.org" root))
           (before (orgsyndb-test-file-text german)))
      (with-current-buffer (orgsyndb-test-visit
                            root "org/procedures/OSDB-0007-ethyl-cinnamate.org")
        (let ((err (should-error (orgsyndb-create-translation)
                                 :type 'user-error)))
          (should (string-match-p "OSDB-0007-ethyl-cinnamate\\.de\\.org"
                                  (error-message-string err)))))
      (should (equal (orgsyndb-test-file-text german) before)))))

(ert-deftest orgsyndb-test-visit-the-other-variant ()
  "Scenario: Visit the other variant."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (with-current-buffer (orgsyndb-test-visit
                          root "org/procedures/OSDB-0007-ethyl-cinnamate.org")
      (orgsyndb-visit-variant)
      (should (equal (buffer-file-name (window-buffer (selected-window)))
                     (expand-file-name
                      "org/procedures/OSDB-0007-ethyl-cinnamate.de.org"
                      root))))))

;;;; Problem locations

(ert-deftest orgsyndb-test-export-problem-on-the-org-source ()
  "Scenario: Export problem on the Org source."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (let ((source (expand-file-name
                   "org/procedures/OSDB-0007-ethyl-cinnamate.org" root)))
      (should (equal (mapcar (lambda (field)
                               (orgsyndb-problem-location
                                root "build/export/OSDB-0007-ethyl-cinnamate.md"
                                field "must be a number"))
                             '("products[1].yield_percent" "working_time"
                               "title" "file_name"))
                     (list (list source 18) (list source 13)
                           (list source 1) (list source 1)))))))

(ert-deftest orgsyndb-test-markdown-and-compound-fields ()
  "Scenario: Markdown and compound fields."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (should (equal (cadr (orgsyndb-problem-location
                          root "md/procedures/OSDB-0002-aspirin.md" "status"
                          "unknown"))
                   8))
    (should (equal (cadr (orgsyndb-problem-location
                          root "compounds/acetic-anhydride.toml" "mw"
                          "unknown"))
                   4))))

(ert-deftest orgsyndb-test-line-of-a-toml-error ()
  "Scenario: Line of a TOML error."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (should (equal (orgsyndb-problem-location
                    root "compounds/acetic-anhydride.toml" "toml"
                    "invalid TOML: Invalid value (at line 3, column 8)")
                   (list (expand-file-name "compounds/acetic-anhydride.toml"
                                           root)
                         3)))))

;;;; Diagnostics

(defun orgsyndb-test-place-wrong-weekday (root)
  "Copy the wrong-weekday source into ROOT and return its buffer."
  (copy-file orgsyndb-test-wrong-weekday
             (expand-file-name "org/procedures/" root))
  (orgsyndb-test-visit root "org/procedures/OSDB-0206-wrong-weekday.org"))

(ert-deftest orgsyndb-test-wrong-weekday ()
  "Scenario: Wrong weekday."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (let ((diagnostics (orgsyndb-test-diagnostics
                        (orgsyndb-test-place-wrong-weekday root))))
      (should (= (length diagnostics) 1))
      (pcase-let ((`(,line ,type ,text) (car diagnostics)))
        (should (= line 2))
        (should (eq type :error))
        (should (string-prefix-p "#+CREATED: weekday \"Tue\" does not match"
                                 text))))))

(defun orgsyndb-test-save-and-validate (buffer)
  "Modify BUFFER, save it and wait for the package's runs to finish."
  (with-current-buffer buffer
    (goto-char (point-max))
    (insert "\n")
    (save-buffer))
  (orgsyndb-test-settle))

(ert-deftest orgsyndb-test-markdown-problem-after-a-save ()
  "Scenario: Markdown problem after a save.
Also: A run stopped by the export keeps earlier problems."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (let* ((orgsyndb-validate-on-save t)
           (buffer (orgsyndb-test-visit root
                                        "md/procedures/OSDB-0002-aspirin.md"))
           (status (lambda ()
                     (cl-find-if (lambda (diagnostic)
                                   (and (= (car diagnostic) 8)
                                        (eq (cadr diagnostic) :error)
                                        (string-prefix-p "status:"
                                                         (nth 2 diagnostic))))
                                 (orgsyndb-test-diagnostics buffer)))))
      (with-current-buffer buffer
        (orgsyndb-test-put "status = \"draft\"" "status = \"done\"¦"))
      (orgsyndb-test-save-and-validate buffer)
      (should (funcall status))
      ;; Scenario: A run stopped by the export keeps earlier problems.
      (make-directory (expand-file-name "org/procedures/nested/" root) t)
      (orgsyndb-test-save-and-validate buffer)
      (should (funcall status))
      (should (string-match-p "subdirectories" (orgsyndb-test-last-message))))))

(ert-deftest orgsyndb-test-export-problem-shown-on-the-org-source ()
  "Scenario: Export problem shown on the Org source."
  (orgsyndb-test-ox-hugo)
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (let ((orgsyndb-validate-on-save t)
          (buffer (orgsyndb-test-visit
                   root "org/procedures/OSDB-0007-ethyl-cinnamate.org")))
      (with-current-buffer buffer
        (orgsyndb-test-put ":working_time 5" ":working_time \"five\"¦"))
      (orgsyndb-test-save-and-validate buffer)
      (should (cl-find-if (lambda (diagnostic)
                            (and (= (car diagnostic) 13)
                                 (eq (cadr diagnostic) :error)
                                 (string-prefix-p "working_time:"
                                                  (nth 2 diagnostic))))
                          (orgsyndb-test-diagnostics buffer))))))

(ert-deftest orgsyndb-test-no-second-copy-of-a-problem-shown-while-typing ()
  "Scenario: No second copy of a problem shown while typing."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (let* ((orgsyndb-validate-on-save t)
           (buffer (orgsyndb-test-place-wrong-weekday root)))
      (orgsyndb-test-save-and-validate buffer)
      (should (= (cl-count-if (lambda (diagnostic)
                                (string-prefix-p "#+CREATED: weekday"
                                                 (nth 2 diagnostic)))
                              (orgsyndb-test-diagnostics buffer))
                 1)))))

(ert-deftest orgsyndb-test-a-preview-build-waits-for-the-validation ()
  "Scenario: A preview build waits for the validation."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (let* ((stub (orgsyndb-test-stub
                  (concat "  serve) echo 'serving http://127.0.0.1:8000/ "
                          "(Ctrl-C to stop)'; exec sleep 60;;\n"
                          "  validate) sleep 1;;\n"
                          "  build) ;;\n")))
           (orgsyndb-program stub)
           (orgsyndb-validate-on-save t)
           (browsed nil)
           (buffer (orgsyndb-test-visit root
                                        "md/procedures/OSDB-0002-aspirin.md")))
      (cl-letf (((symbol-function 'browse-url)
                 (lambda (url &rest _) (push url browsed))))
        (with-current-buffer buffer
          (orgsyndb-serve)
          (orgsyndb-test-wait
           (lambda () (member "begin serve" (orgsyndb-test-stub-log stub))))
          (sleep-for 0.5)
          (dotimes (_ 2)
            (insert "\n")
            (save-buffer))
          (orgsyndb-preview))
        (orgsyndb-test-wait
         (lambda () (member "end build" (orgsyndb-test-stub-log stub))))
        (orgsyndb-test-wait (lambda () browsed)))
      (let ((events (orgsyndb-test-stub-events stub '("validate" "build"))))
        (should (equal events '("begin validate" "end validate"
                                "begin validate" "end validate"
                                "begin build" "end build"))))
      (with-current-buffer buffer
        (orgsyndb-stop-server)))))

(ert-deftest orgsyndb-test-next-error ()
  "Scenario: Next error."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (with-current-buffer (orgsyndb-test-visit
                          root "md/procedures/OSDB-0002-aspirin.md")
      (orgsyndb-test-put "status = \"draft\"" "status = \"done\"¦")
      (save-buffer)
      (let ((compilation (orgsyndb-validate)))
        (orgsyndb-test-wait
         (lambda ()
           (with-current-buffer compilation
             (not (get-buffer-process (current-buffer))))))
        (orgsyndb-test-settle)
        (with-current-buffer compilation
          (goto-char (point-min))
          (next-error))
        (should (equal (buffer-file-name (window-buffer (selected-window)))
                       (expand-file-name
                        "md/procedures/OSDB-0002-aspirin.de.md" root)))
        (with-current-buffer (window-buffer (selected-window))
          (should (= (line-number-at-pos) 8)))))))

(ert-deftest orgsyndb-test-flymake-by-default ()
  "Scenario: Flymake by default."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (let ((orgsyndb-diagnostics 'flymake))
      (with-current-buffer (orgsyndb-test-visit
                            root "org/procedures/OSDB-0007-ethyl-cinnamate.org")
        (should flymake-mode)
        (should (memq #'orgsyndb-flymake flymake-diagnostic-functions))))))

(ert-deftest orgsyndb-test-checker-defined-when-flycheck-loads ()
  "Scenario: Checker defined when Flycheck loads."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (let ((recorded nil)
          (buffer (orgsyndb-test-place-wrong-weekday root)))
      (unwind-protect
          (progn
            (defalias 'flycheck-define-generic-checker
              (lambda (name _docstring &rest properties)
                (push (cons name properties) recorded)))
            (defalias 'flycheck-error-new-at
              (lambda (line _column &optional level message &rest _)
                (list line level message)))
            (require 'orgsyndb-flycheck)
            (should (null recorded))
            (provide 'flycheck)
            (let* ((checker (assq 'orgsyndb recorded))
                   (start (plist-get (cdr checker) :start))
                   (reported nil))
              (should checker)
              (with-current-buffer buffer
                (funcall start 'orgsyndb
                         (lambda (status &optional errors)
                           (setq reported (cons status errors)))))
              (should (eq (car reported) 'finished))
              (should (= (length (cdr reported)) 1))
              (should (equal (car (nth 0 (cdr reported))) 2))
              (should (eq (nth 1 (nth 0 (cdr reported))) 'error))))
        (setq features (delq 'flycheck features))
        (fmakunbound 'flycheck-define-generic-checker)
        (fmakunbound 'flycheck-error-new-at)))))

;;;; Timestamps on save

(defun orgsyndb-test-save-at (buffer time)
  "Modify BUFFER and save it with the current time fixed at TIME."
  (with-current-buffer buffer
    (goto-char (point-max))
    (insert "\n")
    (orgsyndb-test-at time
      (save-buffer))))

(ert-deftest orgsyndb-test-org-in-winter ()
  "Scenario: Org in winter."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (let* ((system-time-locale "de_DE.UTF-8")
           (file "org/procedures/OSDB-0007-ethyl-cinnamate.org")
           (buffer (orgsyndb-test-visit root file)))
      (should (equal (orgsyndb-test-file-line (expand-file-name file root)
                                              "#+LAST_MODIFIED:")
                     "#+LAST_MODIFIED: [2026-10-20 Tue 10:22:50]"))
      (orgsyndb-test-save-at buffer "2026-01-15T10:00:00Z")
      (should (equal (orgsyndb-test-file-line (expand-file-name file root)
                                              "#+LAST_MODIFIED:")
                     "#+LAST_MODIFIED: [2026-01-15 Thu 11:00:00]")))))

(ert-deftest orgsyndb-test-markdown-in-summer-and-winter ()
  "Scenario: Markdown in summer and winter.
Also: The fall-back hour."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (let* ((file (expand-file-name "md/procedures/OSDB-0002-aspirin.md" root))
           (buffer (find-file-noselect file)))
      (pcase-dolist (`(,time . ,line)
                     '(("2026-07-15T10:00:00Z"
                        . "lastmod = 2026-07-15T12:00:00+02:00")
                       ("2026-01-15T10:00:00Z"
                        . "lastmod = 2026-01-15T11:00:00+01:00")
                       ;; Scenario: The fall-back hour.
                       ("2026-10-25T00:30:00Z"
                        . "lastmod = 2026-10-25T02:30:00+02:00")
                       ("2026-10-25T01:30:00Z"
                        . "lastmod = 2026-10-25T02:30:00+01:00")))
        (orgsyndb-test-save-at buffer time)
        (should (equal (orgsyndb-test-file-line file "lastmod") line))))))

(ert-deftest orgsyndb-test-the-users-own-time-stamp-settings ()
  "Scenario: The user's own time-stamp settings."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (let ((file (expand-file-name "md/procedures/OSDB-0002-aspirin.md" root)))
      (unwind-protect
          (progn
            (setq-default time-stamp-pattern "10/Updated: <%Y>")
            (add-hook 'before-save-hook #'time-stamp)
            (orgsyndb-test-save-at (find-file-noselect file)
                                   "2026-07-15T10:00:00Z"))
        (setq-default time-stamp-pattern nil)
        (remove-hook 'before-save-hook #'time-stamp))
      (should (equal (orgsyndb-test-file-line file "lastmod")
                     "lastmod = 2026-07-15T12:00:00+02:00")))))

(ert-deftest orgsyndb-test-global-settings-untouched ()
  "Scenario: Global settings untouched."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (let ((format (default-value 'time-stamp-format)))
      (unwind-protect
          (progn
            (setq-default time-stamp-format "%Y")
            (with-current-buffer (orgsyndb-test-visit
                                  root "md/procedures/OSDB-0002-aspirin.md")
              (should (equal (default-value 'time-stamp-format) "%Y"))
              (should (local-variable-p 'time-stamp-format))
              (should-not (equal time-stamp-format "%Y"))))
        (setq-default time-stamp-format format)))))

(ert-deftest orgsyndb-test-timestamps-turned-off ()
  "Scenario: Turned off."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (let* ((orgsyndb-update-timestamps nil)
           (file (expand-file-name "md/procedures/OSDB-0002-aspirin.md" root))
           (before (orgsyndb-test-file-line file "lastmod")))
      (orgsyndb-test-save-at (find-file-noselect file) "2026-07-15T10:00:00Z")
      (should (equal (orgsyndb-test-file-line file "lastmod") before)))))

;;;; New procedure and new compound

(ert-deftest orgsyndb-test-new-markdown-procedure-in-german ()
  "Scenario: New Markdown procedure in German."
  (orgsyndb-test-with (root orgsyndb-test-collection)
    (let* ((stub (orgsyndb-test-stub
                  (concat "  new) touch \"$2/md/procedures/"
                          "OSDB-0010-ethylacetat.de.md\"; "
                          "echo md/procedures/OSDB-0010-ethylacetat.de.md"
                          ";;\n")))
           (orgsyndb-program stub))
      (with-current-buffer (orgsyndb-test-visit root "orgsyndb.toml")
        (orgsyndb-test-answering '("md" "de" "Ethylacetat herstellen")
          (let ((current-prefix-arg '(4)))
            (call-interactively #'orgsyndb-new-procedure))))
      (should (member (list "-C" (orgsyndb-test-collection-name root) "new"
                            "--md" "--lang" "de" "Ethylacetat" "herstellen")
                      (orgsyndb-test-stub-calls stub)))
      (should (equal (buffer-file-name (window-buffer (selected-window)))
                     (expand-file-name
                      "md/procedures/OSDB-0010-ethylacetat.de.md" root))))))

(ert-deftest orgsyndb-test-new-compound-with-declared-fields ()
  "Scenario: New compound with declared fields."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (with-current-buffer (orgsyndb-test-visit root "orgsyndb.toml")
      (orgsyndb-test-answering '("ethanol" "Ethanol" "Ethanol" "C2H6O"
                                 "46.07" "CCO" "64-17-5" "" "CH-0099"
                                 "alcohols" "reagents")
        (call-interactively #'orgsyndb-new-compound)))
    (let ((file (expand-file-name "compounds/ethanol.toml" root)))
      (should (equal (split-string (orgsyndb-test-file-text file) "\n" t)
                     '("name = \"Ethanol\"" "name_de = \"Ethanol\""
                       "formula = \"C2H6O\"" "mw = 46.07" "smiles = \"CCO\""
                       "cas = \"64-17-5\"" "item_number = \"CH-0099\""
                       "chemical_class = [\"alcohols\"]"
                       "group = \"reagents\"")))
      (should (equal (buffer-file-name (window-buffer (selected-window)))
                     file)))
    (orgsyndb-test-settle)
    (let* ((json (with-temp-buffer
                   (call-process orgsyndb-test-program nil t nil
                                 "-C" root "index")
                   (buffer-string)))
           (entry (cl-find "ethanol"
                           (alist-get 'compounds
                                      (json-parse-string json
                                                         :object-type 'alist
                                                         :array-type 'list))
                           :key (lambda (entry) (alist-get 'key entry))
                           :test #'equal)))
      (should entry)
      (should-not (assq 'error entry)))))

;;;; Preview, PDF and the structure window

(ert-deftest orgsyndb-test-page-urls ()
  "Scenario: Page URLs."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (should (equal (mapcar (lambda (file)
                             (orgsyndb-page-url (expand-file-name file root)))
                           '("org/procedures/OSDB-0007-ethyl-cinnamate.de.org"
                             "compounds/acetone.toml"
                             "md/sequences/SEQ-0001-aspirin-from-wintergreen.md"
                             "orgsyndb.toml"))
                   '("http://127.0.0.1:8000/procedures/osdb-0007/"
                     "http://127.0.0.1:8000/compounds/acetone/"
                     "http://127.0.0.1:8000/sequences/seq-0001/"
                     "http://127.0.0.1:8000/")))))

(defconst orgsyndb-test-serve-stub
  (concat "  serve) echo 'serving http://127.0.0.1:8000/ (Ctrl-C to stop)'; "
          "exec sleep 60;;\n"
          "  build) ;;\n")
  "Stub arms for a server that serves and a build that succeeds.")

(ert-deftest orgsyndb-test-first-preview-starts-the-server ()
  "Scenario: First preview starts the server.
Also: Later preview builds."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (let* ((stub (orgsyndb-test-stub orgsyndb-test-serve-stub))
           (orgsyndb-program stub)
           (browsed nil)
           (url "http://127.0.0.1:8000/compounds/acetone/"))
      (cl-letf (((symbol-function 'browse-url)
                 (lambda (url &rest _) (push url browsed))))
        (with-current-buffer (orgsyndb-test-visit root "compounds/acetone.toml")
          (orgsyndb-preview)
          (orgsyndb-test-wait (lambda () browsed))
          (should (member (list "-C" (orgsyndb-test-collection-name root)
                                "serve" "--port" "8000")
                          (orgsyndb-test-stub-calls stub)))
          (should (equal browsed (list url)))
          ;; Scenario: Later preview builds.
          (orgsyndb-preview)
          (orgsyndb-test-wait (lambda () (= (length browsed) 2)))
          (should (member (list "-C" (orgsyndb-test-collection-name root)
                                "build")
                          (orgsyndb-test-stub-calls stub)))
          (should (equal browsed (list url url)))
          (orgsyndb-stop-server))))))

(ert-deftest orgsyndb-test-unpublished-variant ()
  "Scenario: Unpublished variant."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (let ((orgsyndb-program (orgsyndb-test-stub orgsyndb-test-serve-stub)))
      (cl-letf (((symbol-function 'browse-url) #'ignore))
        (with-current-buffer (orgsyndb-test-visit
                              root
                              "org/procedures/OSDB-0007-ethyl-cinnamate.org")
          (should (equal (alist-get 'site_language (orgsyndb-index)) "de"))
          (orgsyndb-preview)
          (should (string-match-p "OSDB-0007-ethyl-cinnamate\\.de\\.org"
                                  (orgsyndb-test-messages)))
          (orgsyndb-stop-server))))))

(ert-deftest orgsyndb-test-the-procedures-pdf ()
  "Scenario: The procedure's PDF."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (let ((orgsyndb-program
           (orgsyndb-test-stub
            (concat "  pdf) mkdir -p \"$2/pdf\"; echo pdf > "
                    "\"$2/pdf/OSDB-0007-ethyl-cinnamate.de.pdf\";;\n")))
          (pdf (expand-file-name "pdf/OSDB-0007-ethyl-cinnamate.de.pdf" root)))
      (with-current-buffer (orgsyndb-test-visit
                            root "org/procedures/OSDB-0007-ethyl-cinnamate.org")
        (orgsyndb-pdf))
      (orgsyndb-test-wait (lambda () (find-buffer-visiting pdf))))))

(ert-deftest orgsyndb-test-structure-image-and-text ()
  "Scenario: Image and text."
  (orgsyndb-test-with (root orgsyndb-test-demo)
    (with-current-buffer (orgsyndb-test-visit root "compounds/acetone.toml")
      (erase-buffer)
      (insert "isopentyl-acetate and acetone\n")
      (orgsyndb-structure-mode 1)
      (unwind-protect
          (let ((structure (get-buffer "*orgsyndb structure*")))
            (should structure)
            (goto-char (point-min))
            (search-forward "isopentyl")
            (orgsyndb-structure-update)
            (with-current-buffer structure
              (when (image-type-available-p 'svg)
                (let ((image (get-text-property (point-min) 'display)))
                  (should (eq (car-safe image) 'image))
                  (should (equal (plist-get (cdr image) :file)
                                 (expand-file-name
                                  "static/structures/isopentyl-acetate.svg"
                                  root)))))
              (should (string-match-p "Isopentyl acetate" (buffer-string))))
            (goto-char (point-min))
            (search-forward "aceto")
            (orgsyndb-structure-update)
            (with-current-buffer structure
              (should-not (or (get-text-property (point-min) 'display)
                              (next-single-property-change (point-min)
                                                           'display)))
              (should (string-match-p "Acetone" (buffer-string)))))
        (orgsyndb-structure-mode -1)
        (set-buffer-modified-p nil)))))

;;;; Command menu

(defun orgsyndb-test-suffix-commands (layout)
  "Return every `:command' value in the transient LAYOUT."
  (cond ((vectorp layout)
         (orgsyndb-test-suffix-commands (append layout nil)))
        ((consp layout)
         (let ((own (and (keywordp (car layout))
                         (plist-member layout :command)
                         (list (plist-get layout :command)))))
           (append own
                   (cl-mapcan #'orgsyndb-test-suffix-commands
                              (if own (cl-remove (plist-get layout :command)
                                                 layout)
                                layout)))))
        (t nil)))

(ert-deftest orgsyndb-test-one-binding ()
  "Scenario: One binding."
  (orgsyndb-test-require)
  (let ((bound nil))
    (cl-labels ((walk (map prefix)
                  (map-keymap
                   (lambda (event binding)
                     (let ((keys (vconcat prefix (vector event))))
                       (cond ((keymapp binding) (walk binding keys))
                             (binding (push (cons keys binding) bound)))))
                   map)))
      (walk orgsyndb-mode-map []))
    (should (equal bound (list (cons (kbd "C-c C-;") 'orgsyndb-dispatch)))))
  (should (equal (sort (delete-dups (orgsyndb-test-suffix-commands
                                     (get 'orgsyndb-dispatch
                                          'transient--layout)))
                       #'string<)
                 (sort (list 'orgsyndb-new-procedure 'orgsyndb-new-compound
                             'orgsyndb-insert-compound 'orgsyndb-visit-variant
                             'orgsyndb-create-translation 'orgsyndb-validate
                             'orgsyndb-preview 'orgsyndb-serve
                             'orgsyndb-stop-server 'orgsyndb-pdf
                             'orgsyndb-structure-mode
                             'orgsyndb-preview-on-save-mode
                             'orgsyndb-refresh-index)
                       #'string<))))

(provide 'orgsyndb-tests)

;;; orgsyndb-tests.el ends here

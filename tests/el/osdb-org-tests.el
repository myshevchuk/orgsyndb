;;; osdb-org-tests.el --- ERT tests for osdb-org.el  -*- lexical-binding: t; -*-

;;; Commentary:

;; Run with:
;;
;;   emacs -Q --batch -l tests/el/osdb-org-tests.el \
;;         -f ert-run-tests-batch-and-exit
;;
;; The suite loads tools/osdb-org.el relative to its own location, reads
;; fixtures from tests/fixtures/, and needs neither Org nor ox-hugo nor
;; tomelr nor the network.  When the library is missing or fails to load,
;; every test fails with that reason instead of the run aborting.
;;
;; Each test names its scenario in its docstring.  Scenarios that the
;; specs state with "R" compare whole report lines, with R the directory
;; as given to `osdb-org-examine'.

;;; Code:

(require 'ert)
(require 'cl-lib)
(require 'subr-x)

(defconst osdb-org-test-directory
  (file-name-directory (expand-file-name (or load-file-name
                                             buffer-file-name)))
  "The directory of this file.")

(defconst osdb-org-test-repo
  (expand-file-name "../../" osdb-org-test-directory)
  "The root of the repository, as a directory name.")

(defconst osdb-org-test-library
  (expand-file-name "tools/osdb-org" osdb-org-test-repo)
  "The library to test, without its suffix.")

(defconst osdb-org-test-fixtures
  (expand-file-name "tests/fixtures/" osdb-org-test-repo)
  "The fixture directory, as a directory name.")

(defconst osdb-org-test-propyl-name "OSDB-0003-propyl-acetate.org"
  "The file name of the valid source that most tests copy.")

(defconst osdb-org-test-ambiguous-name "OSDB-0004-ambiguous-hour.org"
  "The file name of the valid source with a fall-back hour.")

(defconst osdb-org-test-m
  "the export sets date, lastmod, ai_model and the export file name itself"
  "The ending of the messages about forbidden routes (M in the specs).")

(defun osdb-org-test-require ()
  "Load the library, or signal an error naming why it cannot load."
  (unless (featurep 'osdb-org)
    (unless (file-exists-p (concat osdb-org-test-library ".el"))
      (error "The library tools/osdb-org.el is missing (%s.el)"
             osdb-org-test-library))
    (require 'osdb-org osdb-org-test-library)))

;; A failure here is reported again by each test.
(ignore-errors (osdb-org-test-require))

;;;; Files and edits

(defmacro osdb-org-test-with-dir (var &rest body)
  "Run BODY with VAR bound to a new temporary directory, removed after."
  (declare (indent 1))
  `(let ((,var (make-temp-file "osdb-org-test " t)))
     (unwind-protect (progn ,@body)
       (delete-directory ,var t))))

(defun osdb-org-test-fixture (relative)
  "Return the absolute name of the fixture RELATIVE."
  (expand-file-name relative osdb-org-test-fixtures))

(defun osdb-org-test-read (file)
  "Return the contents of FILE, decoded as UTF-8 with LF line ends."
  (with-temp-buffer
    (let ((coding-system-for-read 'utf-8-unix))
      (insert-file-contents file))
    (buffer-string)))

(defun osdb-org-test-write (file text)
  "Write TEXT to FILE as UTF-8 with LF line ends."
  (let ((coding-system-for-write 'utf-8-unix))
    (with-temp-file file (insert text))))

(defun osdb-org-test-write-bytes (file bytes)
  "Write the unibyte string BYTES to FILE unchanged."
  (let ((coding-system-for-write 'no-conversion))
    (with-temp-buffer
      (set-buffer-multibyte nil)
      (insert bytes)
      (write-region nil nil file nil 'silent))))

(defun osdb-org-test-valid (name)
  "Return the text of the valid fixture source NAME."
  (osdb-org-test-read (osdb-org-test-fixture (concat "valid/org/" name))))

(defun osdb-org-test-propyl ()
  "Return the text of the valid propyl-acetate source."
  (osdb-org-test-valid osdb-org-test-propyl-name))

(defun osdb-org-test-ambiguous ()
  "Return the text of the valid source with a fall-back hour."
  (osdb-org-test-valid osdb-org-test-ambiguous-name))

(defun osdb-org-test--keyword-regexp (keyword)
  "Return a regexp that matches the line of the file keyword KEYWORD."
  (format "^#\\+%s:.*$" keyword))

(defun osdb-org-test--assert-unique (text keyword)
  "Fail unless TEXT has exactly one `#+KEYWORD:' line."
  (let ((case-fold-search nil)
        (regexp (osdb-org-test--keyword-regexp keyword))
        (count 0)
        (start 0))
    (while (string-match regexp text start)
      (setq count (1+ count)
            start (match-end 0)))
    (unless (= count 1)
      (error "Fixture has %d `#+%s:' lines, not exactly one" count keyword))))

(defun osdb-org-test-map-line (text keyword function)
  "Replace the one `#+KEYWORD:' line of TEXT by FUNCTION of that line.
Signal an error when TEXT does not have exactly one such line."
  (osdb-org-test--assert-unique text keyword)
  (let ((case-fold-search nil))
    (replace-regexp-in-string (osdb-org-test--keyword-regexp keyword)
                              function text t t)))

(defun osdb-org-test-replace-line (text keyword new)
  "Replace the one `#+KEYWORD:' line of TEXT by the lines NEW."
  (osdb-org-test-map-line text keyword (lambda (_line) new)))

(defun osdb-org-test-set-keyword (text keyword value)
  "Set the one `#+KEYWORD:' line of TEXT to VALUE, and change nothing else."
  (osdb-org-test-replace-line text keyword (format "#+%s: %s" keyword value)))

(defun osdb-org-test-remove-keyword (text keyword)
  "Remove the one `#+KEYWORD:' line of TEXT."
  (osdb-org-test--assert-unique text keyword)
  (let ((case-fold-search nil))
    (replace-regexp-in-string
     (format "^#\\+%s:.*\n" keyword) "" text t t)))

(defun osdb-org-test-add-after (text keyword lines)
  "Add LINES to TEXT after its one `#+KEYWORD:' line."
  (osdb-org-test-map-line text keyword
                          (lambda (line) (concat line "\n" lines))))

(defun osdb-org-test-add-under-first-heading (text lines)
  "Add LINES to TEXT directly after its first heading."
  (let ((case-fold-search nil))
    (unless (string-match "^\\* .*\n" text)
      (error "Fixture has no heading"))
    (concat (substring text 0 (match-end 0)) lines "\n"
            (substring text (match-end 0)))))

(defun osdb-org-test-edit (text edits)
  "Apply EDITS, in order, to TEXT and return the result.
Each edit is (set KEYWORD VALUE), (remove KEYWORD) or
\(add-after KEYWORD LINES)."
  (dolist (edit edits text)
    (setq text
          (pcase edit
            (`(set ,keyword ,value)
             (osdb-org-test-set-keyword text keyword value))
            (`(remove ,keyword)
             (osdb-org-test-remove-keyword text keyword))
            (`(add-after ,keyword ,lines)
             (osdb-org-test-add-after text keyword lines))
            (_ (error "Unknown edit %S" edit))))))

;;;; Examining and comparing

(defun osdb-org-test-examine-files (files)
  "Examine a new temporary directory holding FILES.
FILES is an alist of file names and texts.  Return the directory, which
is removed by then, consed to the result of `osdb-org-examine'."
  (osdb-org-test-with-dir root
    (dolist (file files)
      (osdb-org-test-write (expand-file-name (car file) root) (cdr file)))
    (cons root (osdb-org-examine root))))

(defun osdb-org-test-examine-text (name text)
  "Examine a new temporary directory holding the file NAME with TEXT.
Return what `osdb-org-test-examine-files' returns."
  (osdb-org-test-examine-files (list (cons name text))))

(defun osdb-org-test-lines (result)
  "Return the report lines of RESULT, a value of `osdb-org-examine'."
  (mapcar (lambda (entry) (osdb-org-problem-line (car entry) (cdr entry)))
          (cdr result)))

(defun osdb-org-test-line (root name field message &optional severity)
  "Return the report line for the file NAME in ROOT.
FIELD and MESSAGE complete it, and SEVERITY defaults to \"error\"."
  (format "%s/%s:%s: %s: %s" (directory-file-name root) name field
          (or severity "error") message))

(defun osdb-org-test-assert-one (result field text &optional suffix)
  "Check that RESULT has one problem: an error on FIELD containing TEXT.
When SUFFIX is non-nil, the problem's path also ends with it."
  (let ((problems (cdr result)))
    (should (equal (length problems) 1))
    (let ((problem (cdr (car problems))))
      (should (equal (nth 0 problem) field))
      (should (equal (nth 1 problem) "error"))
      (should (string-search text (nth 2 problem))))
    (when suffix
      (should (string-suffix-p suffix (car (car problems)))))))

(defun osdb-org-test-assert-fixture (case file field message)
  "Examine the fixture org-invalid/CASE/org and check its one problem.
The problem is an error on FIELD, with exactly MESSAGE, on the file FILE,
and there is no source."
  (let ((result (osdb-org-examine
                 (osdb-org-test-fixture
                  (format "org-invalid/%s/org" case)))))
    (should (null (car result)))
    (should (equal (mapcar #'cdr (cdr result))
                   (list (list field "error" message))))
    (should (string-suffix-p file (car (car (cdr result)))))))

(defun osdb-org-test-sole-source (name text)
  "Examine the file NAME with TEXT and return its one source.
Fail when there is a problem or another source."
  (pcase-let ((`(,_root . ,result) (osdb-org-test-examine-text name text)))
    (should (equal (osdb-org-test-lines result) nil))
    (should (equal (length (car result)) 1))
    (car (car result))))

(defun osdb-org-test-assert-lines (name text expected)
  "Examine the file NAME with TEXT and compare its report lines.
EXPECTED is a list of (FIELD MESSAGE) for errors on that file, in order."
  (pcase-let ((`(,root . ,result) (osdb-org-test-examine-text name text)))
    (should (equal (osdb-org-test-lines result)
                   (mapcar (lambda (entry)
                             (osdb-org-test-line root name (nth 0 entry)
                                                 (nth 1 entry)))
                           expected)))
    result))

(defun osdb-org-test-propyl-lines (text expected)
  "Examine the propyl-acetate source with TEXT, expecting EXPECTED lines.
See `osdb-org-test-assert-lines' for EXPECTED."
  (osdb-org-test-assert-lines osdb-org-test-propyl-name text expected))

(defun osdb-org-test-rfc (instants)
  "Return INSTANTS formatted by `osdb-org-rfc3339'."
  (mapcar #'osdb-org-rfc3339 instants))

;;;; org-export: examining a directory

(ert-deftest osdb-org-test-entries-of-the-org-root ()
  "Scenario: Entries of the Org root."
  (osdb-org-test-require)
  (osdb-org-test-with-dir root
    (let ((name osdb-org-test-propyl-name))
      (osdb-org-test-write (expand-file-name name root)
                           (osdb-org-test-propyl))
      (make-symbolic-link "missing-target"
                          (expand-file-name ".#OSDB-0003-x.org" root))
      (osdb-org-test-write (expand-file-name ".OSDB-0005-hidden.org" root)
                           "not a procedure\n")
      (osdb-org-test-write (expand-file-name "_index.md" root) "index\n")
      (make-directory (expand-file-name "nested.org" root))
      (osdb-org-test-write (expand-file-name "notes.txt" root) "notes\n")
      (let* ((result (osdb-org-examine root))
             (source (car (car result))))
        (should (equal (length (car result)) 1))
        (should (equal (plist-get source :path)
                       (expand-file-name name root)))
        (should (equal (plist-get source :stem)
                       "OSDB-0003-propyl-acetate"))
        (should (equal (plist-get source :date) "2026-10-19T17:42:05+02:00"))
        (should (equal (plist-get source :lastmod)
                       "2026-10-19T18:30:00+02:00"))
        (should (null (plist-get source :ai-model)))
        (should (equal (osdb-org-test-lines result)
                       (list (osdb-org-test-line
                              root "nested.org" "file_name"
                              (concat "subdirectories are not supported; "
                                      "move its files to the top level"))
                             (osdb-org-test-line
                              root "notes.txt" "file_name"
                              "not a procedure file; ignored" "warning"))))))))

(ert-deftest osdb-org-test-subdirectory-in-the-org-root ()
  "Scenario: Subdirectory in the Org root."
  (osdb-org-test-require)
  (let ((result (osdb-org-examine
                 (osdb-org-test-fixture "org-invalid/subdirectory/org"))))
    (should (null (car result)))
    (osdb-org-test-assert-one result "file_name"
                              "subdirectories are not supported" "nested")))

(ert-deftest osdb-org-test-problem-line-format ()
  "Scenario: Problem line format."
  (osdb-org-test-require)
  (let* ((root (osdb-org-test-fixture "org-invalid/wrong-weekday/org"))
         (expected (format (concat "%s/OSDB-0206-wrong-weekday.org:#+CREATED:"
                                   " error: weekday \"Tue\" does not match "
                                   "2026-10-19 (Mon)")
                           root)))
    (dolist (given (list root (concat root "/")))
      (should (equal (osdb-org-test-lines (osdb-org-examine given))
                     (list expected))))))

(ert-deftest osdb-org-test-problems-in-path-order ()
  "Scenario: Problems in path order."
  (osdb-org-test-require)
  (let* ((result
          (cdr (osdb-org-test-examine-files
                (list (cons "OSDB-0206-wrong-weekday.org"
                            (osdb-org-test-read
                             (osdb-org-test-fixture
                              (concat "org-invalid/wrong-weekday/org/"
                                      "OSDB-0206-wrong-weekday.org"))))
                      (cons "OSDB-0201-missing-created.org"
                            (osdb-org-test-read
                             (osdb-org-test-fixture
                              (concat "org-invalid/missing-created/org/"
                                      "OSDB-0201-missing-created.org"))))))))
         (problems (cdr result)))
    (should (equal (length problems) 2))
    (should (string-suffix-p "OSDB-0201-missing-created.org"
                             (car (nth 0 problems))))
    (should (string-suffix-p "OSDB-0206-wrong-weekday.org"
                             (car (nth 1 problems))))))

(ert-deftest osdb-org-test-file-name-and-keywords-together ()
  "Scenario: File name and keywords together."
  (osdb-org-test-require)
  (osdb-org-test-assert-lines
   "osdb-0201-missing-created.org"
   (osdb-org-test-read
    (osdb-org-test-fixture
     "org-invalid/missing-created/org/OSDB-0201-missing-created.org"))
   '(("file_name"
      "must be named OSDB-NNNN-short-slug.org, e.g. OSDB-0001-ethyl-acetate.org, or OSDB-0001-ethyl-acetate.de.org with a language")
     ("#+CREATED" "keyword missing"))))

(ert-deftest osdb-org-test-language-code-in-an-org-file-name ()
  "Scenario: Language code in an Org file name."
  (osdb-org-test-require)
  (should (null (osdb-org-check-file-name "OSDB-0100-baseline.en.org")))
  (should (equal (osdb-org-check-file-name "OSDB-0100-baseline.fr.org")
                 '(("file_name" "error"
                    "unknown language code \".fr\"; use de or en, or none")))))

(ert-deftest osdb-org-test-invalid-utf-8-suppresses-every-other-check ()
  "Scenario: Invalid UTF-8 suppresses every other check."
  (osdb-org-test-require)
  (osdb-org-test-with-dir root
    (let* ((name "osdb-0100-bad-bytes.org")
           (text (osdb-org-test-remove-keyword (osdb-org-test-propyl)
                                               "CREATED"))
           (newline (string-search "\n" text)))
      (osdb-org-test-write-bytes
       (expand-file-name name root)
       (concat (encode-coding-string (substring text 0 newline) 'utf-8-unix)
               (unibyte-string 255)
               (encode-coding-string (substring text newline) 'utf-8-unix)))
      (should (equal (osdb-org-test-lines (osdb-org-examine root))
                     (list (osdb-org-test-line
                            root name "front_matter"
                            "file is not valid UTF-8")))))))

(ert-deftest osdb-org-test-unreadable-source ()
  "Scenario: Unreadable source."
  (osdb-org-test-require)
  (osdb-org-test-with-dir root
    (let* ((name "osdb-0100-unreadable.org")
           (file (expand-file-name name root)))
      (osdb-org-test-write file (osdb-org-test-propyl))
      (set-file-modes file 0)
      (skip-unless (not (file-readable-p file)))
      (should (equal (osdb-org-test-lines (osdb-org-examine root))
                     (list (osdb-org-test-line
                            root name "front_matter"
                            "cannot read file: Permission denied")))))))

(ert-deftest osdb-org-test-byte-order-mark-and-crlf-line-ends ()
  "Scenario: Byte-order mark and CRLF line ends."
  (osdb-org-test-require)
  (osdb-org-test-with-dir root
    (osdb-org-test-write-bytes
     (expand-file-name osdb-org-test-propyl-name root)
     (concat (unibyte-string #xef #xbb #xbf)
             (encode-coding-string
              (replace-regexp-in-string "\n" "\r\n" (osdb-org-test-propyl))
              'utf-8-unix)))
    (let* ((result (osdb-org-examine root))
           (source (car (car result))))
      (should (equal (osdb-org-test-lines result) nil))
      (should (equal (length (car result)) 1))
      (should (equal (plist-get source :date) "2026-10-19T17:42:05+02:00"))
      (should (equal (plist-get source :lastmod)
                     "2026-10-19T18:30:00+02:00")))))

(ert-deftest osdb-org-test-missing-time-zone ()
  "Scenario: Missing time zone."
  (osdb-org-test-require)
  (should (osdb-org-zone-available-p "Europe/Berlin"))
  (should (osdb-org-zone-available-p))
  (should-not (osdb-org-zone-available-p "Nowhere/Nothing")))

(ert-deftest osdb-org-test-library-loads-alone ()
  "Scenario: Library loads alone."
  (osdb-org-test-require)
  (should (featurep 'osdb-org))
  (dolist (feature '(org ox-hugo tomelr))
    (should-not (featurep feature))))

;;;; org-export: exported timestamps

(defun osdb-org-test-times (text created last-modified)
  "Return the source that TEXT gives with CREATED and LAST-MODIFIED set."
  (osdb-org-test-sole-source
   osdb-org-test-propyl-name
   (osdb-org-test-edit text `((set "CREATED" ,created)
                              (set "LAST_MODIFIED" ,last-modified)))))

(ert-deftest osdb-org-test-summer-time ()
  "Scenario: Summer time."
  (osdb-org-test-require)
  (let ((source (osdb-org-test-sole-source
                 osdb-org-test-propyl-name
                 (osdb-org-test-set-keyword (osdb-org-test-propyl)
                                            "CREATED"
                                            "[2026-10-19 Mon 17:42:05]"))))
    (should (equal (plist-get source :date) "2026-10-19T17:42:05+02:00"))))

(ert-deftest osdb-org-test-winter-time-last-second-before-the-spring-change ()
  "Scenario: Winter time, last second before the spring change."
  (osdb-org-test-require)
  (let ((source (osdb-org-test-times (osdb-org-test-propyl)
                                     "[2026-03-29 Sun 01:59:59]"
                                     "[2026-03-29 Sun 03:00:00]")))
    (should (equal (plist-get source :date) "2026-03-29T01:59:59+01:00"))
    (should (equal (plist-get source :lastmod) "2026-03-29T03:00:00+02:00"))))

(ert-deftest osdb-org-test-fall-back-hour-out-of-wall-clock-order ()
  "Scenario: Fall-back hour out of wall-clock order."
  (osdb-org-test-require)
  (let ((source (osdb-org-test-times (osdb-org-test-ambiguous)
                                     "[2026-10-25 Sun 02:50:00]"
                                     "[2026-10-25 Sun 02:10:00]")))
    (should (equal (plist-get source :date) "2026-10-25T02:50:00+02:00"))
    (should (equal (plist-get source :lastmod) "2026-10-25T02:10:00+01:00"))))

(ert-deftest osdb-org-test-equal-times-in-the-fall-back-hour ()
  "Scenario: Equal times in the fall-back hour."
  (osdb-org-test-require)
  (let ((source (osdb-org-test-times (osdb-org-test-ambiguous)
                                     "[2026-10-25 Sun 02:30:00]"
                                     "[2026-10-25 Sun 02:30:00]")))
    (should (equal (plist-get source :date) "2026-10-25T02:30:00+02:00"))
    (should (equal (plist-get source :lastmod) "2026-10-25T02:30:00+02:00"))))

(ert-deftest osdb-org-test-instants-of-a-wall-clock-time ()
  "Scenario: Instants of a wall-clock time."
  (osdb-org-test-require)
  (should (equal (osdb-org-test-rfc
                  (osdb-org-local-instants 2026 10 19 17 42 5))
                 '("2026-10-19T17:42:05+02:00")))
  (should (equal (osdb-org-test-rfc
                  (osdb-org-local-instants 2026 10 25 2 30 0))
                 '("2026-10-25T02:30:00+02:00" "2026-10-25T02:30:00+01:00")))
  (should (null (osdb-org-local-instants 2026 3 29 2 30 0))))

(ert-deftest osdb-org-test-choice-among-fall-back-instants ()
  "Scenario: Choice among fall-back instants."
  (osdb-org-test-require)
  (let ((chosen (osdb-org-export-instants
                 (osdb-org-local-instants 2026 10 25 2 50 0)
                 (osdb-org-local-instants 2026 10 25 2 10 0))))
    (should (equal (osdb-org-rfc3339 (car chosen))
                   "2026-10-25T02:50:00+02:00"))
    (should (equal (osdb-org-rfc3339 (cdr chosen))
                   "2026-10-25T02:10:00+01:00"))))

;;;; procedure-schema: Org file-level keywords

(ert-deftest osdb-org-test-missing-creation-keyword ()
  "Scenario: Missing creation keyword."
  (osdb-org-test-require)
  (osdb-org-test-assert-fixture "missing-created"
                                "OSDB-0201-missing-created.org"
                                "#+CREATED" "keyword missing"))

(ert-deftest osdb-org-test-keyword-given-twice ()
  "Scenario: Keyword given twice."
  (osdb-org-test-require)
  (osdb-org-test-assert-fixture "duplicate-created"
                                "OSDB-0202-duplicate-created.org"
                                "#+CREATED" "appears more than once"))

(ert-deftest osdb-org-test-active-timestamp ()
  "Scenario: Active timestamp."
  (osdb-org-test-require)
  (osdb-org-test-assert-fixture
   "active-timestamp" "OSDB-0203-active-timestamp.org" "#+LAST_MODIFIED"
   (concat "\"<2026-10-19 Mon 17:42:05>\" must be an inactive timestamp in "
           "square brackets, [YYYY-MM-DD Day hh:mm:ss]")))

(ert-deftest osdb-org-test-timestamp-without-seconds ()
  "Scenario: Timestamp without seconds."
  (osdb-org-test-require)
  (osdb-org-test-assert-fixture
   "missing-seconds" "OSDB-0204-missing-seconds.org" "#+CREATED"
   "\"[2026-10-19 Mon 17:42]\" must have the form [YYYY-MM-DD Day hh:mm:ss]"))

(ert-deftest osdb-org-test-impossible-calendar-date ()
  "Scenario: Impossible calendar date."
  (osdb-org-test-require)
  (osdb-org-test-assert-fixture
   "invalid-date" "OSDB-0205-invalid-date.org" "#+CREATED"
   "\"[2026-02-30 Mon 10:00:00]\" is not a valid date"))

(ert-deftest osdb-org-test-invalid-date-does-not-cascade ()
  "Scenario: Invalid date does not cascade."
  (osdb-org-test-require)
  (let ((lines (osdb-org-test-lines
                (osdb-org-examine
                 (osdb-org-test-fixture "org-invalid/invalid-date/org")))))
    (should (equal (length lines) 1))
    (should-not (string-search "weekday" (car lines)))
    (should-not (string-search "earlier than" (car lines)))))

(ert-deftest osdb-org-test-weekday-does-not-match-the-date ()
  "Scenario: Weekday does not match the date."
  (osdb-org-test-require)
  (osdb-org-test-assert-fixture
   "wrong-weekday" "OSDB-0206-wrong-weekday.org" "#+CREATED"
   "weekday \"Tue\" does not match 2026-10-19 (Mon)"))

(ert-deftest osdb-org-test-local-time-skipped-by-the-spring-clock-change ()
  "Scenario: Local time skipped by the spring clock change."
  (osdb-org-test-require)
  (osdb-org-test-assert-fixture
   "nonexistent-local-time" "OSDB-0207-nonexistent-local-time.org"
   "#+CREATED"
   (concat "\"[2026-03-29 Sun 02:30:00]\" does not exist in Europe/Berlin "
           "(skipped by the clock change)")))

(ert-deftest osdb-org-test-modification-before-creation ()
  "Scenario: Modification before creation."
  (osdb-org-test-require)
  (osdb-org-test-assert-fixture
   "last-modified-before-created"
   "OSDB-0208-last-modified-before-created.org" "#+LAST_MODIFIED"
   "is earlier than #+CREATED"))

(ert-deftest osdb-org-test-modification-before-creation-across-the-fold ()
  "Scenario: Modification before creation across the fall-back hour."
  (osdb-org-test-require)
  (pcase-let ((`(,_root . ,result)
               (osdb-org-test-examine-text
                osdb-org-test-ambiguous-name
                (osdb-org-test-edit
                 (osdb-org-test-ambiguous)
                 '((set "CREATED" "[2026-10-25 Sun 03:00:00]")
                   (set "LAST_MODIFIED" "[2026-10-25 Sun 02:10:00]"))))))
    (osdb-org-test-assert-one result "#+LAST_MODIFIED"
                              "is earlier than #+CREATED")))

(ert-deftest osdb-org-test-ambiguous-fall-back-hour-can-be-in-order ()
  "Scenario: Ambiguous fall-back hour can be in order."
  (osdb-org-test-require)
  (let* ((result (osdb-org-examine (osdb-org-test-fixture "valid/org")))
         (source (cl-find "OSDB-0004-ambiguous-hour" (car result)
                          :key (lambda (entry) (plist-get entry :stem))
                          :test #'equal)))
    (should (equal (osdb-org-test-lines result) nil))
    (should source)
    (should (equal (plist-get source :ai-model) "claude-sonnet-5-5"))))

(ert-deftest osdb-org-test-empty-ai-model ()
  "Scenario: Empty AI model."
  (osdb-org-test-require)
  (osdb-org-test-assert-fixture "bad-ai-model" "OSDB-0209-bad-ai-model.org"
                                "#+AI_MODEL"
                                "must be a model identifier or none"))

(ert-deftest osdb-org-test-org-file-name-breaks-the-naming-rule ()
  "Scenario: Org file name breaks the naming rule."
  (osdb-org-test-require)
  (osdb-org-test-assert-fixture
   "bad-org-file-name" "osdb-0210-lowercase.org" "file_name"
   (concat "must be named OSDB-NNNN-short-slug.org, e.g. "
           "OSDB-0001-ethyl-acetate.org, or OSDB-0001-ethyl-acetate.de.org "
           "with a language")))

(ert-deftest osdb-org-test-invalid-time ()
  "Scenario: Invalid time."
  (osdb-org-test-require)
  (osdb-org-test-propyl-lines
   (osdb-org-test-set-keyword (osdb-org-test-propyl) "CREATED"
                              "[2026-10-19 Mon 24:00:00]")
   '(("#+CREATED"
      "\"[2026-10-19 Mon 24:00:00]\" is not a valid time"))))

(defconst osdb-org-test-dependent-cases
  '((1 ((set "CREATED" "[2026-10-19 Mon 17:42]")
        (set "LAST_MODIFIED" "[2026-10-18 Sun 09:00:00]"))
       (("#+CREATED" "\"[2026-10-19 Mon 17:42]\" must have the form [YYYY-MM-DD Day hh:mm:ss]")))
    (2 ((set "LAST_MODIFIED" "[2026-03-29 Sun 02:30:00]"))
       (("#+LAST_MODIFIED" "\"[2026-03-29 Sun 02:30:00]\" does not exist in Europe/Berlin (skipped by the clock change)")))
    (3 ((add-after "CREATED" "#+CREATED: [2026-10-19 Mon 17:42:05]")
        (set "LAST_MODIFIED" "[2026-10-18 Sun 09:00:00]"))
       (("#+CREATED" "appears more than once")))
    (4 ((remove "LAST_MODIFIED"))
       (("#+LAST_MODIFIED" "keyword missing")))
    (5 ((set "CREATED" "<2026-10-19 Mon 17:42:05>")
        (set "LAST_MODIFIED" "[2026-02-30 Mon 10:00:00]")
        (set "AI_MODEL" "two words"))
       (("#+CREATED" "\"<2026-10-19 Mon 17:42:05>\" must be an inactive timestamp in square brackets, [YYYY-MM-DD Day hh:mm:ss]")
        ("#+LAST_MODIFIED" "\"[2026-02-30 Mon 10:00:00]\" is not a valid date")
        ("#+AI_MODEL" "must be a model identifier or none")))
    (6 ((set "CREATED" "[2026-03-29 Mon 02:30:00]"))
       (("#+CREATED" "weekday \"Mon\" does not match 2026-03-29 (Sun)")))
    (7 ((set "CREATED" "[2026-02-30 Mon 25:00:00]"))
       (("#+CREATED" "\"[2026-02-30 Mon 25:00:00]\" is not a valid date")))
    (8 ((set "CREATED" "[2026-10-19 Mon 17:42:05>"))
       (("#+CREATED" "\"[2026-10-19 Mon 17:42:05>\" must have the form [YYYY-MM-DD Day hh:mm:ss]")))
    (9 ((set "AI_MODEL" "example-model-1"))
       nil))
  "The cases of the dependent checks: number, edits, expected errors.
The edits apply to the valid propyl-acetate source.  Each expected error
is a field and a message.")

(defun osdb-org-test-dependent (number)
  "Check case NUMBER of `osdb-org-test-dependent-cases'."
  (osdb-org-test-require)
  (let* ((entry (assq number osdb-org-test-dependent-cases))
         (result (osdb-org-test-propyl-lines
                  (osdb-org-test-edit (osdb-org-test-propyl) (nth 1 entry))
                  (nth 2 entry))))
    (when (= number 9)
      (should (equal (plist-get (car (car result)) :ai-model)
                     "example-model-1")))))

(ert-deftest osdb-org-test-dependent-checks-1 ()
  "Scenario: Dependent checks of the keywords, case 1."
  (osdb-org-test-dependent 1))

(ert-deftest osdb-org-test-dependent-checks-2 ()
  "Scenario: Dependent checks of the keywords, case 2."
  (osdb-org-test-dependent 2))

(ert-deftest osdb-org-test-dependent-checks-3 ()
  "Scenario: Dependent checks of the keywords, case 3."
  (osdb-org-test-dependent 3))

(ert-deftest osdb-org-test-dependent-checks-4 ()
  "Scenario: Dependent checks of the keywords, case 4."
  (osdb-org-test-dependent 4))

(ert-deftest osdb-org-test-dependent-checks-5 ()
  "Scenario: Dependent checks of the keywords, case 5."
  (osdb-org-test-dependent 5))

(ert-deftest osdb-org-test-dependent-checks-6 ()
  "Scenario: Dependent checks of the keywords, case 6."
  (osdb-org-test-dependent 6))

(ert-deftest osdb-org-test-dependent-checks-7 ()
  "Scenario: Dependent checks of the keywords, case 7."
  (osdb-org-test-dependent 7))

(ert-deftest osdb-org-test-dependent-checks-8 ()
  "Scenario: Dependent checks of the keywords, case 8."
  (osdb-org-test-dependent 8))

(ert-deftest osdb-org-test-dependent-checks-9 ()
  "Scenario: Dependent checks of the keywords, case 9."
  (osdb-org-test-dependent 9))

(ert-deftest osdb-org-test-keyword-lines ()
  "Scenario: Keyword lines."
  (osdb-org-test-require)
  (dolist (line '("#+created: [2026-10-19 Mon 17:42:05]"
                  "  #+CREATED:   [2026-10-19 Mon 17:42:05]  "))
    (ert-info (line :prefix "Line: ")
      (osdb-org-test-sole-source
       osdb-org-test-propyl-name
       (osdb-org-test-replace-line (osdb-org-test-propyl) "CREATED" line))))
  (pcase-let ((`(,_root . ,result)
               (osdb-org-test-examine-text
                osdb-org-test-propyl-name
                (osdb-org-test-replace-line
                 (osdb-org-test-propyl) "CREATED"
                 (concat "#+begin_example\n"
                         "#+CREATED: [2026-10-19 Mon 17:42:05]\n"
                         "#+END_EXAMPLE")))))
    (osdb-org-test-assert-one result "#+CREATED" "keyword missing")))

(ert-deftest osdb-org-test-ascii-digits-and-ascii-trimming ()
  "Scenario: ASCII digits and ASCII trimming."
  (osdb-org-test-require)
  (dolist (value (list (concat "[" (string #x662 #x660 #x662 #x666)
                               "-10-19 Mon 17:42:05]")
                       (concat "[2026-10-19 Mon 17:42:05]" (string #xa0))))
    (ert-info (value :prefix "Value: ")
      (osdb-org-test-propyl-lines
       (osdb-org-test-set-keyword (osdb-org-test-propyl) "CREATED" value)
       (list (list "#+CREATED"
                   (format "\"%s\" must have the form %s" value
                           "[YYYY-MM-DD Day hh:mm:ss]")))))))

;;;; procedure-schema: exported values come only from the keywords

(defconst osdb-org-test-forbidden-keywords
  '("DATE" "HUGO_LASTMOD" "HUGO_AUTO_SET_LASTMOD"
    "HUGO_FRONT_MATTER_KEY_REPLACE" "EXPORT_FILE_NAME" "HUGO_BASE_DIR"
    "HUGO_BASE_CONTENT_FOLDER" "HUGO_SECTION" "HUGO_BUNDLE" "SETUPFILE"
    "INCLUDE")
  "The keywords that must not occur, in report order.")

(defun osdb-org-test-with-extra-lines (lines)
  "Return the propyl-acetate source with LINES added after `#+AI_MODEL:'."
  (osdb-org-test-add-after (osdb-org-test-propyl) "AI_MODEL" lines))

(ert-deftest osdb-org-test-keywords-that-would-set-exported-values ()
  "Scenario: Keywords that would set exported values."
  (osdb-org-test-require)
  (dolist (keyword osdb-org-test-forbidden-keywords)
    (ert-info (keyword :prefix "Keyword: ")
      (osdb-org-test-propyl-lines
       (osdb-org-test-with-extra-lines
        (format "#+%s: x" (downcase keyword)))
       (list (list (concat "#+" keyword)
                   (concat "must not be used; " osdb-org-test-m)))))))

(ert-deftest osdb-org-test-custom-front-matter-that-would-set-values ()
  "Scenario: Custom front matter that would set exported values."
  (osdb-org-test-require)
  (let ((date '("#+HUGO_CUSTOM_FRONT_MATTER"
                "must not set :date; the export writes it from #+CREATED"))
        (lastmod '("#+HUGO_CUSTOM_FRONT_MATTER"
                   "must not set :lastmod; the export writes it from #+LAST_MODIFIED")))
    (dolist (case `(("#+HUGO_CUSTOM_FRONT_MATTER: :ai_model \"example-model-1\""
                     (("#+HUGO_CUSTOM_FRONT_MATTER"
                       "must not set :ai_model; the export writes it from #+AI_MODEL")))
                    ("#+HUGO_CUSTOM_FRONT_MATTER: :Date 2026-01-01"
                     (,date))
                    ("#+HUGO_CUSTOM_FRONT_MATTER: :lastmod 2026-01-01 :date 2026-01-01"
                     (,date ,lastmod))))
      (ert-info ((car case) :prefix "Line: ")
        (osdb-org-test-propyl-lines
         (osdb-org-test-with-extra-lines (car case)) (cadr case))))))

(ert-deftest osdb-org-test-colons-inside-values-are-not-keys ()
  "Scenario: Colons inside values are not keys."
  (osdb-org-test-require)
  (osdb-org-test-propyl-lines
   (osdb-org-test-with-extra-lines
    (concat "#+HUGO_CUSTOM_FRONT_MATTER: :notes \"see :date\" "
            ":refs '(\":lastmod\" \"a :ai_model\")"))
   nil))

(ert-deftest osdb-org-test-export-properties-and-logbooks ()
  "Scenario: Export properties and logbooks."
  (osdb-org-test-require)
  (let ((propyl (osdb-org-test-propyl)))
    (dolist (case
             `((,(osdb-org-test-add-after
                  propyl "AI_MODEL" "#+PROPERTY: EXPORT_FILE_NAME other")
                (("#+PROPERTY" ,(concat "must not set EXPORT_FILE_NAME; "
                                        osdb-org-test-m))))
               (,(osdb-org-test-add-after
                  propyl "AI_MODEL" "#+property: log_into_drawer t")
                (("#+PROPERTY" ,(concat "must not set LOG_INTO_DRAWER; "
                                        osdb-org-test-m))))
               (,(osdb-org-test-add-under-first-heading
                  propyl (concat ":PROPERTIES:\n"
                                 ":EXPORT_DATE: [2026-01-01 Thu]\n"
                                 ":END:"))
                ((":EXPORT_DATE:" ,(concat "must not be used; "
                                           osdb-org-test-m))))
               (,(osdb-org-test-add-under-first-heading
                  propyl (concat ":LOGBOOK:\n"
                                 "- Note taken on [2026-01-01 Thu 10:00]\n"
                                 ":END:"))
                ((":LOGBOOK:" ,(concat "must not be used; "
                                       osdb-org-test-m))))))
      (ert-info ((cadr (car (cadr case))) :prefix "Expected: ")
        (osdb-org-test-propyl-lines (car case) (cadr case))))))

(ert-deftest osdb-org-test-extra-front-matter ()
  "Scenario: Extra front matter."
  (osdb-org-test-require)
  (let ((propyl (osdb-org-test-propyl))
        (block "ai_model = \"example-model-1\"\n#+end_src")
        (expected `((":front_matter_extra"
                     ,(concat "must not be used; " osdb-org-test-m)))))
    (dolist (text
             (list (osdb-org-test-add-under-first-heading
                    propyl (concat "#+begin_src toml :front_matter_extra t\n"
                                   block))
                   (osdb-org-test-add-under-first-heading
                    propyl (concat "#+header: :front_matter_extra t\n"
                                   "#+begin_src toml\n" block))
                   (osdb-org-test-add-after
                    propyl "AI_MODEL"
                    "#+PROPERTY: header-args:toml :front_matter_extra t")
                   (osdb-org-test-add-under-first-heading
                    propyl (concat ":PROPERTIES:\n"
                                   ":header-args:toml: :front_matter_extra t\n"
                                   ":END:"))))
      (osdb-org-test-propyl-lines text expected))))

(ert-deftest osdb-org-test-forbidden-lines-inside-blocks-are-ignored ()
  "Scenario: Forbidden lines inside blocks are ignored."
  (osdb-org-test-require)
  (osdb-org-test-propyl-lines
   (osdb-org-test-with-extra-lines
    (mapconcat #'identity
               '("#+begin_example"
                 "#+DATE: x"
                 "#+HUGO_CUSTOM_FRONT_MATTER: :date x"
                 ":EXPORT_DATE: x"
                 ":LOGBOOK:"
                 "#+header: :front_matter_extra t"
                 "#+end_example")
               "\n"))
   nil))

;;;; Templates

(defun osdb-org-test-filled-template (template name)
  "Examine the Org TEMPLATE, filled as `new' fills it, saved as NAME.
Return what `osdb-org-examine' returns for its directory."
  (let ((text (osdb-org-test-read
               (expand-file-name (concat "templates/" template)
                                 osdb-org-test-repo))))
    (cdr (osdb-org-test-examine-text
          name
          (string-replace "osdb-0000" "osdb-0001"
                          (string-replace "OSDB-0000" "OSDB-0001" text))))))

(ert-deftest osdb-org-test-org-template-passes-the-org-checks ()
  "Scenario: Org template passes the Org checks."
  (osdb-org-test-require)
  (let ((result (osdb-org-test-filled-template
                 "procedure.org" "OSDB-0001-template.org")))
    (should (equal (osdb-org-test-lines result) nil))
    (should (equal (length (car result)) 1))))

(ert-deftest osdb-org-test-german-org-template-passes-the-org-checks ()
  "Scenario: German Org template passes the Org checks."
  (osdb-org-test-require)
  (let ((result (osdb-org-test-filled-template
                 "procedure.de.org" "OSDB-0001-vorlage.de.org")))
    (should (equal (osdb-org-test-lines result) nil))
    (should (equal (length (car result)) 1))
    (should (equal (plist-get (car (car result)) :stem)
                   "OSDB-0001-vorlage.de"))))

(provide 'osdb-org-tests)

;;; osdb-org-tests.el ends here

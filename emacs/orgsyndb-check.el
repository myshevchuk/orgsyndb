;;; orgsyndb-check.el --- Diagnostics and validation  -*- lexical-binding: t; -*-

;;; Commentary:

;; Problems in two layers: the Org front end's checks of an Org source,
;; run on the buffer text, and the problems of the last `orgsyndb
;; validate', which runs in the background after each save.  Both are
;; placed on the line of the field they name and reported through the
;; Flymake backend `orgsyndb-flymake'; `orgsyndb-validate' lists them in
;; a compilation buffer.

;;; Code:

(require 'orgsyndb-core)
(require 'flymake)
(require 'compile)

(defcustom orgsyndb-validate-on-save t
  "Non-nil means saving a collection file validates the collection.
The validation runs in the background, and its problems appear in the
buffers of the collection's files."
  :type 'boolean
  :group 'orgsyndb)

(defconst orgsyndb--problem-regexp
  "^\\([^:\n]+\\):\\(.*?\\): \\(error\\|warning\\): \\(.*\\)$"
  "A problem line of the program: path, field, severity and message.")

;;;; Problem locations

(defun orgsyndb--source-path (path)
  "Return the collection-relative PATH of a problem's file, with an
export `build/export/<stem>.md' mapped to its source
`org/procedures/<stem>.org'."
  (if (string-match "\\`build/export/\\(.+\\)\\.md\\'" path)
      (concat "org/procedures/" (match-string 1 path) ".org")
    path))

(defconst orgsyndb--org-keywords
  '(("title" . "TITLE") ("slug" . "HUGO_SLUG") ("tags" . "HUGO_TAGS")
    ("date" . "CREATED") ("lastmod" . "LAST_MODIFIED")
    ("ai_model" . "AI_MODEL"))
  "The Org keywords that write front-matter keys.")

(defun orgsyndb--first-line (lines regexp &optional fold)
  "Return the number, from 1, of the first of LINES that REGEXP matches,
ignoring case with FOLD, or nil."
  (let ((case-fold-search fold)
        (number 0))
    (cl-loop for line in lines
             do (cl-incf number)
             when (string-match-p regexp line) return number)))

(defun orgsyndb--field-line (text type field &optional message)
  "Return the line, from 1, of the file text TEXT where a problem of
FIELD with MESSAGE belongs.  TYPE is `org', `md' or `toml'."
  (let ((lines (split-string text "\n"))
        (key (if (string-match "\\`[^[.]+" field) (match-string 0 field)
               field)))
    (or
     (and (member field '("front_matter" "toml")) message
          (string-match "at line \\([0-9]+\\)" message)
          (string-to-number (match-string 1 message)))
     (pcase type
       ('org
        (let ((keyword (or (cdr (assoc key orgsyndb--org-keywords))
                           (and (string-prefix-p "#+" key)
                                (substring key 2)))))
          (cond
           (keyword
            (orgsyndb--first-line
             lines (format "\\`[ \t]*#\\+%s:" (regexp-quote keyword)) t))
           ((equal key "scope")
            (orgsyndb--first-line
             lines "\\`[ \t]*#\\+name:[ \t]*scope[ \t]*\\'" t))
           (t
            (orgsyndb--first-line
             lines
             (format (concat "\\`[ \t]*#\\+hugo_custom_front_matter:"
                             ".*\\(?:[ \t]\\|:\\):%s\\(?:[ \t]\\|\\'\\)")
                     (regexp-quote key))
             t)))))
       ((or 'md 'toml)
        (let* ((quoted (regexp-quote key))
               (name (format "\\(?:%s\\|\"%s\"\\)" quoted quoted))
               (regexp (concat "\\`[ \t]*" name "[ \t]*="
                               "\\|\\`[ \t]*\\[\\[?[ \t]*" name "[ \t]*[].]"))
               (front (if (and (eq type 'md) lines
                               (string-match-p "\\`\\+\\+\\+[ \t\r]*\\'"
                                               (car lines)))
                          (let ((end (cl-position-if
                                      (lambda (line)
                                        (string-match-p
                                         "\\`\\+\\+\\+[ \t\r]*\\'" line))
                                      lines :start 1)))
                            (cl-subseq lines 0 end))
                        lines)))
          (orgsyndb--first-line front regexp))))
     1)))

(defun orgsyndb--file-type (file)
  "Return the type of FILE's text: `org', `md' or `toml'."
  (pcase (file-name-extension file)
    ("org" 'org)
    ("md" 'md)
    (_ 'toml)))

(defun orgsyndb-problem-location (collection path field &optional message)
  "Return (FILE LINE), where a problem of PATH and FIELD with MESSAGE
belongs in COLLECTION.
PATH is relative to COLLECTION; an export `build/export/<stem>.md'
names its source `org/procedures/<stem>.org'.  FILE is absolute, and
LINE counts from 1: the line that a TOML parse error MESSAGE names, the
line of the field's key in Markdown front matter or a TOML file, in an
Org source the keyword, scope table or custom front matter that writes
the field, and 1 when nothing matches."
  (let* ((file (expand-file-name (orgsyndb--source-path path) collection))
         (buffer (find-buffer-visiting file))
         (text (cond (buffer (with-current-buffer buffer
                               (buffer-substring-no-properties
                                (point-min) (point-max))))
                     ((file-readable-p file)
                      (with-temp-buffer
                        (insert-file-contents file)
                        (buffer-string))))))
    (list file (if text
                   (orgsyndb--field-line text (orgsyndb--file-type file)
                                         field message)
                 1))))

;;;; The problems the package keeps

(defvar orgsyndb--problems (make-hash-table :test #'equal)
  "Map each collection to (EXPORT . VALIDATOR), two tables mapping each
collection-relative file to its problems, each (FIELD SEVERITY
MESSAGE): those of the Org export and those of the validator.")

(defun orgsyndb--parse-problems (output)
  "Return the problem lines of OUTPUT as (PATH FIELD SEVERITY MESSAGE)."
  (let ((start 0)
        found)
    (while (string-match orgsyndb--problem-regexp output start)
      (push (list (match-string 1 output) (match-string 2 output)
                  (match-string 3 output) (match-string 4 output))
            found)
      (setq start (match-end 0)))
    (nreverse found)))

(defun orgsyndb--take-problems (root output errors)
  "Keep the problems of a validation of ROOT that printed OUTPUT and
ERRORS, and show them in the collection's buffers."
  (let* ((complete (string-match-p "^validated [0-9]+ files: " errors))
         (kept (gethash root orgsyndb--problems))
         (export (make-hash-table :test #'equal))
         (validator (if (or complete (null kept))
                        (make-hash-table :test #'equal)
                      (cdr kept)))
         (problems (orgsyndb--parse-problems output)))
    (pcase-dolist (`(,path . ,problem) problems)
      (let ((table (if (string-prefix-p "org/procedures/" path) export
                     validator))
            (file (orgsyndb--source-path path)))
        (when (or complete (eq table export))
          (puthash file (append (gethash file table) (list problem)) table))))
    (puthash root (cons export validator) orgsyndb--problems)
    (unless complete
      (let ((first (cl-find "error" problems :key #'caddr :test #'equal)))
        (message "orgsyndb validate stopped: %s"
                 (if first
                     (pcase-let ((`(,path ,field ,_ ,text) first))
                       (format "%s:%s: %s" path field text))
                   (orgsyndb--error-text errors)))))
    (dolist (buffer (buffer-list))
      (with-current-buffer buffer
        (when (and (bound-and-true-p orgsyndb-mode)
                   (equal orgsyndb--root root))
          (orgsyndb--diagnostics-changed))))))

(defun orgsyndb--diagnostics-changed ()
  "Have the buffer's diagnostics front end report again."
  (cond ((bound-and-true-p flymake-mode) (flymake-start))
        ((and (bound-and-true-p flycheck-mode) (fboundp 'flycheck-buffer))
         (funcall 'flycheck-buffer))))

(defun orgsyndb--kept-problems (root file)
  "Return (EXPORT . VALIDATOR), the problems kept for FILE of ROOT."
  (let ((kept (gethash root orgsyndb--problems))
        (relative (file-relative-name file root)))
    (and kept
         (cons (gethash relative (car kept))
               (gethash relative (cdr kept))))))

(defun orgsyndb--typing-problems ()
  "Return the problems of the Org front end in the buffer's text."
  (when (eq orgsyndb--kind 'org-procedure)
    (let ((text (buffer-substring-no-properties (point-min) (point-max))))
      (append (osdb-org-check-file-name
               (file-name-nondirectory buffer-file-name))
              (car (osdb-org-lint text))
              (car (osdb-org-scope text))))))

(defun orgsyndb--buffer-problems ()
  "Return the problems of the current buffer as (LINE SEVERITY TEXT).
They are the Org front end's problems of the buffer text and the kept
problems of the last validation, an export problem left out when the
front end reports the same one."
  (when (and orgsyndb--root buffer-file-name)
    (let* ((typing (orgsyndb--typing-problems))
           (kept (orgsyndb--kept-problems orgsyndb--root buffer-file-name))
           (text (buffer-substring-no-properties (point-min) (point-max)))
           (type (orgsyndb--file-type buffer-file-name)))
      (mapcar (pcase-lambda (`(,field ,severity ,message))
                (list (orgsyndb--field-line text type field message)
                      severity (format "%s: %s" field message)))
              (append typing
                      (cl-remove-if (lambda (problem)
                                      (member problem typing))
                                    (car kept))
                      (cdr kept))))))

(defun orgsyndb-flymake (report-fn &rest _)
  "Report the buffer's problems to Flymake through REPORT-FN.
Each covers the line of its field and reads `<field>: <message>'."
  (funcall report-fn
           (mapcar (pcase-lambda (`(,line ,severity ,text))
                     (save-excursion
                       (goto-char (point-min))
                       (forward-line (1- line))
                       (let ((beg (line-beginning-position))
                             (end (line-end-position)))
                         (flymake-make-diagnostic
                          (current-buffer) beg
                          (if (and (= beg end) (< end (point-max)))
                              (1+ end)
                            end)
                          (if (equal severity "error") :error :warning)
                          text))))
                   (orgsyndb--buffer-problems))))

;;;; Validation

(defun orgsyndb--validate-later (root)
  "Validate the collection ROOT in the background when its turn comes."
  (orgsyndb--enqueue
   root 'validate
   (lambda (finish)
     (orgsyndb--start root '("validate") :name "orgsyndb validate"
                      :on-exit (lambda (status output errors)
                                 (unwind-protect
                                     (unless (eq status 'killed)
                                       (orgsyndb--take-problems root output
                                                                errors))
                                   (funcall finish status)))))))

(defconst orgsyndb--compilation-regexp
  "^\\([^:\n]+\\):\\(.*?\\): \\(?:error\\|\\(warning\\)\\): \\(.*\\)$"
  "A problem line, group 3 matching only a warning.")

(defun orgsyndb--compilation-file ()
  "Return the file of the problem line just matched."
  (orgsyndb--source-path (match-string 1)))

(defun orgsyndb--compilation-line ()
  "Return the line of the problem line just matched."
  (save-match-data
    (let ((path (match-string 1))
          (field (match-string 2))
          (message (match-string 4)))
      (cadr (orgsyndb-problem-location default-directory path field
                                       message)))))

(define-compilation-mode orgsyndb-validation-mode "OrgSynDB validation"
  "The output of `orgsyndb validate', its problem lines leading to the
lines of the fields they name."
  (setq-local compilation-error-regexp-alist
              (list (list orgsyndb--compilation-regexp
                          #'orgsyndb--compilation-file
                          #'orgsyndb--compilation-line
                          nil '(3)))))

;;;###autoload
(defun orgsyndb-validate ()
  "Validate the current collection in a compilation buffer.
Each problem line leads, with `next-error', to the line of the field it
names.  Return the buffer."
  (interactive)
  (let* ((root (orgsyndb--current-root))
         (name (format "*orgsyndb validate %s*"
                       (file-name-nondirectory (directory-file-name root))))
         (buffer (get-buffer-create name)))
    (orgsyndb--enqueue
     root 'validate-buffer
     (lambda (finish)
       (let* ((default-directory root)
              (compilation (compilation-start
                            (mapconcat #'shell-quote-argument
                                       (cons orgsyndb-program
                                             (orgsyndb--arguments
                                              root '("validate")))
                                       " ")
                            #'orgsyndb-validation-mode
                            (lambda (_mode) name)))
              (process (get-buffer-process compilation)))
         (if (null process)
             (funcall finish 'failed)
           (process-put process 'orgsyndb root)
           (with-current-buffer compilation
             (add-hook 'compilation-finish-functions
                       (lambda (_buffer status) (funcall finish status))
                       nil t))))))
    buffer))

(provide 'orgsyndb-check)

;;; orgsyndb-check.el ends here

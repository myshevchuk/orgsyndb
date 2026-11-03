;;; orgsyndb-files.el --- Variants, translations and new files  -*- lexical-binding: t; -*-

;;; Commentary:

;; Commands that visit and create the files of a collection: another
;; language variant of a procedure or sequence, a translation of a
;; procedure, a new procedure through `orgsyndb new', and a new compound
;; file prompted from the schema and the declared fields.

;;; Code:

(require 'orgsyndb-core)

;;;; Language variants

;;;###autoload
(defun orgsyndb-visit-variant ()
  "Visit another language variant of the current procedure or sequence."
  (interactive)
  (let* ((root (orgsyndb--current-root))
         (file buffer-file-name)
         (id (or (and file (orgsyndb--file-id file))
                 (user-error "This file is no procedure or sequence")))
         (others (cl-remove-if
                  (lambda (path) (equal path file))
                  (mapcar (lambda (entry)
                            (expand-file-name (alist-get 'path entry) root))
                          (orgsyndb--entries-of root id)))))
    (pcase others
      ('nil (user-error "%s has no other variant" id))
      (`(,only) (find-file only))
      (_ (find-file
          (expand-file-name
           (completing-read "Variant: "
                            (mapcar #'file-name-nondirectory others) nil t)
           (file-name-directory file)))))))

(defun orgsyndb--sections (root)
  "Return the section names of ROOT's schema, an alist of language
symbols to lists of names."
  (orgsyndb--schema root 'procedure 'sections))

(defun orgsyndb--text-language (file text sections org)
  "Return the language of the procedure FILE whose text is TEXT.
That is its file-name code, else its `language' value, else `de' when
its section headings, as SECTIONS names them, include more German than
English names, and `en' otherwise.  ORG is non-nil for an Org source."
  (or (orgsyndb--language-code file)
      (let ((case-fold-search nil))
        (and (string-match
              (if org
                  (concat "^[ \t]*#\\+HUGO_CUSTOM_FRONT_MATTER:.*"
                          ":language[ \t]+\"\\([a-z]+\\)\"")
                "^language[ \t]*=[ \t]*\"\\([a-z]+\\)\"")
              text)
             (match-string 1 text)))
      (let ((headings (orgsyndb--headings text org)))
        (if (> (cl-count-if (lambda (heading)
                              (member heading (alist-get 'de sections)))
                            headings)
               (cl-count-if (lambda (heading)
                              (member heading (alist-get 'en sections)))
                            headings))
            "de"
          "en"))))

(defun orgsyndb--heading-regexp (org)
  "Return the regexp of a section heading, Org's when ORG is non-nil;
group 1 is the heading's text."
  (if org "^\\* +\\(.*?\\)[ \t]*$" "^## +\\(.*?\\)[ \t]*$"))

(defun orgsyndb--headings (text org)
  "Return the section headings of TEXT, in order."
  (let ((regexp (orgsyndb--heading-regexp org))
        (start 0)
        found)
    (while (string-match regexp text start)
      (push (match-string 1 text) found)
      (setq start (match-end 0)))
    (nreverse found)))

(defun orgsyndb--translate (text org from to time sections)
  "Return the translation skeleton of the procedure TEXT.
The front matter, or in Org the lines before the first heading, keeps
its values, except that the creation and modification times become
TIME and a `language' value becomes TO; each section heading of the
language FROM becomes the heading at the same position in TO's list of
SECTIONS.  ORG is non-nil for an Org source."
  (let* ((case-fold-search nil)
         (from-names (alist-get (intern from) sections))
         (to-names (alist-get (intern to) sections))
         (split (if org
                    (if (string-match "^\\* " text) (match-beginning 0)
                      (length text))
                  (if (string-match (concat "\\`\\+\\+\\+[ \t\r]*\n"
                                            "\\(?:.*\n\\)*?\\+\\+\\+[ \t\r]*$")
                                    text)
                      (match-end 0)
                    0)))
         (head (substring text 0 split))
         (body (substring text split)))
    (setq head
          (if org
              (let ((stamp (orgsyndb--org-timestamp time))
                    (case-fold-search t))
                (thread-last
                  head
                  (replace-regexp-in-string
                   "^\\([ \t]*#\\+\\(?:CREATED\\|LAST_MODIFIED\\):[ \t]*\\).*$"
                   (lambda (line)
                     (concat (match-string 1 line) stamp)))
                  (replace-regexp-in-string
                   "\\(:language[ \t]+\\)\"[a-z]+\""
                   (lambda (pair)
                     (concat (match-string 1 pair) "\"" to "\"")))))
            (let ((stamp (orgsyndb--rfc3339 time)))
              (thread-last
                head
                (replace-regexp-in-string
                 "^\\(\\(?:date\\|lastmod\\)[ \t]*=[ \t]*\\).*$"
                 (lambda (line) (concat (match-string 1 line) stamp)))
                (replace-regexp-in-string
                 "^\\(language[ \t]*=[ \t]*\\)\"[a-z]+\""
                 (lambda (line)
                   (concat (match-string 1 line) "\"" to "\"")))))))
    (setq body
          (replace-regexp-in-string
           (orgsyndb--heading-regexp org)
           (lambda (line)
             (let* ((heading (and (string-match
                                   (orgsyndb--heading-regexp org) line)
                                  (match-string 1 line)))
                    (position (cl-position heading from-names :test #'equal)))
               (if position
                   (concat (if org "* " "## ") (nth position to-names))
                 line)))
           body t t))
    (concat head body)))

;;;###autoload
(defun orgsyndb-create-translation ()
  "Create the translation of the current procedure into the other
language and visit it.
The new file sits beside the current one and is named after it with
the other language's code.  It holds the current front matter with the
creation and modification times set to now, and the current body with
the section headings of the other language, for the text to be
translated in place."
  (interactive)
  (unless (memq orgsyndb--kind '(org-procedure md-procedure))
    (user-error "This file is no procedure"))
  (let* ((root (orgsyndb--current-root))
         (file buffer-file-name)
         (org (eq orgsyndb--kind 'org-procedure))
         (text (buffer-substring-no-properties (point-min) (point-max)))
         (sections (orgsyndb--sections root))
         (from (orgsyndb--text-language file text sections org))
         (to (if (equal from "de") "en" "de"))
         (name (file-name-nondirectory file))
         (base (replace-regexp-in-string "\\(?:\\.[a-z][a-z]\\)?\\.[a-z]+\\'"
                                         "" name t t))
         (target (expand-file-name (concat base "." to "."
                                           (file-name-extension name))
                                   (file-name-directory file))))
    (when (file-exists-p target)
      (user-error "%s exists already" (file-name-nondirectory target)))
    (let ((coding-system-for-write 'utf-8-unix))
      (write-region (orgsyndb--translate text org from to (orgsyndb--now)
                                         sections)
                    nil target nil 'silent nil 'excl))
    (find-file target)))

;;;; New procedure

;;;###autoload
(defun orgsyndb-new-procedure (title &optional format language)
  "Create a procedure stub titled TITLE with the next free ID, and visit it.
FORMAT is `org', the default, or `md'; LANGUAGE is `none', the default,
`de' or `en'.  Interactively, a prefix argument asks for both."
  (interactive
   (let ((format (if current-prefix-arg
                     (completing-read "Format: " '("org" "md") nil t nil nil
                                      "org")
                   "org"))
         (language (if current-prefix-arg
                       (completing-read "Language: " '("none" "de" "en")
                                        nil t nil nil "none")
                     "none")))
     (list (read-string "Title: ") format language)))
  (let ((root (orgsyndb--current-root)))
    (pcase-let ((`(,status ,output ,errors)
                 (apply #'orgsyndb--call root
                        (append '("new")
                                (and (equal format "md") '("--md"))
                                (and language (not (equal language "none"))
                                     (list "--lang" language))
                                (split-string title)))))
      (unless (eq status 0)
        (error "orgsyndb new: %s"
               (if (stringp status) status (orgsyndb--error-text errors))))
      (find-file (expand-file-name
                  (car (last (split-string output "\n" t "[ \t\r]+")))
                  root)))))

;;;; New compound

(defconst orgsyndb--compound-template
  '(("name" . text) ("name_de" . optional) ("formula" . text)
    ("mw" . number) ("smiles" . text) ("cas" . optional)
    ("structure_image" . image))
  "The built-in keys of a compound file in the order of the application's
compound template, each with how its value is read.")

(defun orgsyndb--toml-value (value)
  "Return VALUE as TOML: a string, a number, a boolean as t or `:false',
or a list of strings."
  (cond ((eq value t) "true")
        ((eq value :false) "false")
        ((numberp value) (format "%s" value))
        ((stringp value)
         (concat "\"" (replace-regexp-in-string "[\"\\\\]" "\\\\\\&" value)
                 "\""))
        ((listp value)
         (concat "[" (mapconcat #'orgsyndb--toml-value value ", ") "]"))))

(defun orgsyndb--read-field (root field)
  "Read a value of the declared FIELD of ROOT in the minibuffer."
  (let ((prompt (format "%s: " (alist-get 'label field))))
    (pcase (alist-get 'type field)
      ("choice"
       (let ((values (mapcar (lambda (entry) (symbol-name (car entry)))
                             (orgsyndb--vocabulary
                              root (alist-get 'vocabulary field)))))
         (if (eq (alist-get 'multiple field) t)
             (completing-read-multiple prompt values nil t)
           (completing-read prompt values nil t))))
      ("boolean" (if (y-or-n-p prompt) t :false))
      ("number" (read-number prompt))
      (_ (read-string prompt)))))

;;;###autoload
(defun orgsyndb-new-compound (key)
  "Create the compound file of KEY in the current collection and visit it.
It asks for the built-in values in the order of the application's
compound template, an empty answer leaving an optional one out, and
then for each declared compound field that is required."
  (interactive (list (read-string "Compound key: ")))
  (let* ((root (orgsyndb--current-root))
         (file (expand-file-name (format "compounds/%s.toml" key) root))
         (lines nil))
    (unless (string-match-p "\\`[a-z0-9]+\\(?:-[a-z0-9]+\\)*\\'" key)
      (user-error "%s is not a lowercase hyphenated key" key))
    (when (file-exists-p file)
      (user-error "compounds/%s.toml exists already" key))
    (pcase-dolist (`(,name . ,how) orgsyndb--compound-template)
      (let ((value (pcase how
                     ('number (read-number (format "%s: " name)))
                     ('image (completing-read
                              "structure_image (empty for none): "
                              (orgsyndb--structure-images root)))
                     ('optional (read-string
                                 (format "%s (empty for none): " name)))
                     (_ (read-string (format "%s: " name))))))
        (unless (equal value "")
          (push (cons name value) lines))))
    (dolist (field (orgsyndb--declarations root 'compound))
      (when (eq (alist-get 'required field) t)
        (push (cons (alist-get 'key field) (orgsyndb--read-field root field))
              lines)))
    (make-directory (file-name-directory file) t)
    (let ((coding-system-for-write 'utf-8-unix))
      (write-region (mapconcat (lambda (line)
                                 (format "%s = %s\n" (car line)
                                         (orgsyndb--toml-value (cdr line))))
                               (nreverse lines) "")
                    nil file nil 'silent nil 'excl))
    (orgsyndb--refresh-index-later root)
    (find-file file)))

(provide 'orgsyndb-files)

;;; orgsyndb-files.el ends here

;;; orgsyndb-xref.el --- Definitions, references and documentation  -*- lexical-binding: t; -*-

;;; Commentary:

;; An `xref' backend for the compound keys and the procedure and
;; sequence IDs of a collection, wherever they appear in its files, and
;; an `eldoc' function that describes the compound or procedure at
;; point.  The definition of a compound key is a buffer describing its
;; substance in the collection's registry.

;;; Code:

(require 'orgsyndb-core)
(require 'xref)
(require 'thingatpt)

(defconst orgsyndb--id-regexp "\\(?:OSDB\\|SEQ\\)-[0-9]\\{4\\}"
  "A procedure or sequence ID.")

(defun orgsyndb--compound-key-p (root word)
  "Return non-nil when WORD is a compound key of ROOT."
  (cl-find word (orgsyndb--compounds root)
           :key (lambda (entry) (alist-get 'key entry)) :test #'equal))

(defun orgsyndb--identifier-at-point ()
  "Return the compound key, procedure ID or sequence ID at point, or nil.
A compound key is a maximal run of lowercase letters, digits and
hyphens that the registry holds."
  (when orgsyndb--root
    (let ((case-fold-search nil))
      (save-excursion
        (if (thing-at-point-looking-at orgsyndb--id-regexp 10)
            (match-string-no-properties 0)
          (let* ((beg (progn (skip-chars-backward "a-z0-9-") (point)))
                 (end (progn (skip-chars-forward "a-z0-9-") (point)))
                 (word (buffer-substring-no-properties beg end)))
            (and (not (string-empty-p word))
                 (orgsyndb--compound-key-p orgsyndb--root word)
                 word)))))))

(defun orgsyndb--xref-backend ()
  "Return `orgsyndb' when an identifier of the collection is at point."
  (and orgsyndb--root
       (ignore-errors (orgsyndb--identifier-at-point))
       'orgsyndb))

(cl-defmethod xref-backend-identifier-at-point ((_backend (eql orgsyndb)))
  (orgsyndb--identifier-at-point))

(cl-defmethod xref-backend-identifier-completion-table
  ((_backend (eql orgsyndb)))
  (let ((root (orgsyndb--current-root)))
    (append (mapcar (lambda (entry) (alist-get 'key entry))
                    (orgsyndb--compounds root))
            (delete-dups
             (mapcar (lambda (entry) (alist-get 'id entry))
                     (append (alist-get 'procedures (orgsyndb-index root))
                             (alist-get 'sequences (orgsyndb-index root))))))))

(defconst orgsyndb--substance-facts
  '((name_de . "German name") (formula . "Formula") (mw . "Molar mass")
    (cas . "CAS") (article_number . "Article no.")
    (short_name . "Short name"))
  "The values of a substance that its buffer shows after its name, in
order, each with its label.")

(defun orgsyndb--substance-buffer (root key)
  "Return the buffer `*orgsyndb KEY*', filled from the index of ROOT.
It describes the substance KEY of the collection's registry: its name,
then, one per line, those of its German name, formula, molar mass, CAS
number, article number and short name that it has.  When the index
gives the substance's page in the lab application, a button that calls
`browse-url' on its address follows; otherwise a line says that it has
none.  The buffer is in `special-mode'."
  (let* ((entry (cl-find key (orgsyndb--compounds root)
                         :key (lambda (entry) (alist-get 'key entry))
                         :test #'equal))
         (data (alist-get 'data entry))
         (url (alist-get 'url entry))
         (buffer (get-buffer-create (format "*orgsyndb %s*" key))))
    (with-current-buffer buffer
      (special-mode)
      (let ((inhibit-read-only t))
        (erase-buffer)
        (insert (or (alist-get 'name data) key) "\n")
        (pcase-dolist (`(,name . ,label) orgsyndb--substance-facts)
          (let ((value (alist-get name data)))
            (when value
              (insert label ": " (format "%s" value)
                      (if (eq name 'mw) " g/mol" "") "\n"))))
        (insert "\n")
        (if (stringp url)
            (insert-text-button "Open its page in the lab application"
                                'action (lambda (_button) (browse-url url))
                                'follow-link t 'help-echo url)
          (insert "It has no page: the collection's registry is a file."))
        (insert "\n")
        (goto-char (point-min))))
    buffer))

(cl-defmethod xref-backend-definitions ((_backend (eql orgsyndb)) identifier)
  (let ((root (orgsyndb--current-root))
        (case-fold-search nil))
    (cond
     ((string-match-p (concat "\\`" orgsyndb--id-regexp "\\'") identifier)
      (let ((record (orgsyndb--definition
                     root identifier
                     (orgsyndb--language-code buffer-file-name))))
        (and record
             (list (xref-make identifier
                              (xref-make-file-location
                               (expand-file-name (alist-get 'path record) root)
                               1 0))))))
     ((orgsyndb--compound-key-p root identifier)
      (list (xref-make identifier
                       (xref-make-buffer-location
                        (orgsyndb--substance-buffer root identifier) 1)))))))

(defun orgsyndb--file-text (file)
  "Return the text of FILE, from the buffer visiting it when there is one."
  (let ((buffer (find-buffer-visiting file)))
    (if buffer
        (with-current-buffer buffer
          (buffer-substring-no-properties (point-min) (point-max)))
      (with-temp-buffer
        (insert-file-contents file)
        (buffer-string)))))

(cl-defmethod xref-backend-references ((_backend (eql orgsyndb)) identifier)
  (let* ((root (orgsyndb--current-root))
         (index (orgsyndb-index root))
         (case-fold-search nil)
         (regexp (if (string-match-p (concat "\\`" orgsyndb--id-regexp "\\'")
                                     identifier)
                     (regexp-quote identifier)
                   (concat "\\(?:\\`\\|[^a-z0-9-]\\)\\("
                           (regexp-quote identifier)
                           "\\)\\(?:[^a-z0-9-]\\|\\'\\)")))
         (found nil))
    (dolist (entry (append (alist-get 'procedures index)
                           (alist-get 'sequences index)))
      (let ((file (expand-file-name (alist-get 'path entry) root))
            (number 0))
        (when (file-exists-p file)
          (dolist (line (split-string (orgsyndb--file-text file) "\n"))
            (cl-incf number)
            (when (string-match regexp line)
              (push (xref-make line (xref-make-file-location
                                     file number
                                     (or (match-beginning 1)
                                         (match-beginning 0))))
                    found))))))
    (nreverse found)))

;;;; Documentation at point

(defun orgsyndb--describe (root identifier language)
  "Return the line that describes IDENTIFIER of ROOT to a file in
LANGUAGE, or nil."
  (if (string-match-p (concat "\\`" orgsyndb--id-regexp "\\'") identifier)
      (let* ((record (orgsyndb--definition root identifier language))
             (front-matter (alist-get 'front_matter record))
             (title (alist-get 'title front-matter))
             (status (alist-get 'status front-matter)))
        (and record
             (concat identifier
                     (and (stringp title) (concat " " title))
                     (and (stringp status)
                          (not (string-prefix-p "SEQ-" identifier))
                          (concat " · " status)))))
    (let* ((data (orgsyndb--compound root identifier))
           (mw (alist-get 'mw data))
           (cas (alist-get 'cas data)))
      (concat identifier ": "
              (string-join
               (delq nil (list (alist-get 'name data)
                               (alist-get 'formula data)
                               (and (numberp mw) (format "%s g/mol" mw))
                               (and (stringp cas) (concat "CAS " cas))))
               " · ")))))

(defun orgsyndb-eldoc (_callback &rest _)
  "Return the line that describes the compound or procedure at point.
A compound is described by its key, name, formula, molecular weight and
CAS number, a procedure by its ID, title and status, and a sequence by
its ID and title.  Return nil elsewhere."
  (when orgsyndb--root
    (let ((identifier (ignore-errors (orgsyndb--identifier-at-point))))
      (and identifier
           (ignore-errors
             (orgsyndb--describe orgsyndb--root identifier
                                 (orgsyndb--language-code
                                  buffer-file-name)))))))

(provide 'orgsyndb-xref)

;;; orgsyndb-xref.el ends here

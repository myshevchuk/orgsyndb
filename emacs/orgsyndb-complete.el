;;; orgsyndb-complete.el --- Completion in collection files  -*- lexical-binding: t; -*-

;;; Commentary:

;; `orgsyndb-completion-at-point' completes the keys and values of the
;; front matter of procedures and sequences, of compound files, of the
;; custom front matter of Org sources and of their scope tables, from
;; the collection index.  `orgsyndb-insert-compound' inserts a compound
;; key chosen by the compound's name.

;;; Code:

(require 'orgsyndb-core)

;;;; Candidates

(defun orgsyndb--candidates (candidates &optional annotations)
  "Return the completion data for CANDIDATES, a list of strings.
ANNOTATIONS, when given, is an alist of candidates to their annotation
texts."
  (cons candidates
        (and annotations
             (lambda (candidate)
               (let ((text (cdr (assoc candidate annotations))))
                 (and text (concat " " text)))))))

(defun orgsyndb--compound-candidates (root)
  "Return the compound keys of ROOT, annotated with name and formula."
  (let (keys annotations)
    (dolist (entry (orgsyndb--compounds root))
      (let ((key (alist-get 'key entry))
            (data (alist-get 'data entry)))
        (push key keys)
        (push (cons key (string-join
                         (delq nil (list (alist-get 'name data)
                                         (alist-get 'formula data)))
                         " · "))
              annotations)))
    (orgsyndb--candidates (nreverse keys) annotations)))

(defun orgsyndb--term-path (terms value)
  "Return the labels of VALUE's ancestors in TERMS and its own, outermost
first, joined by ` › '."
  (let ((labels nil)
        (current value))
    (while current
      (let ((term (alist-get current terms)))
        (push (alist-get 'label term) labels)
        (setq current (and (alist-get 'parent term)
                           (intern (alist-get 'parent term))))))
    (string-join labels " › ")))

(defun orgsyndb--vocabulary-candidates (root name &optional paths)
  "Return the values of the vocabulary NAME of ROOT as candidates.
Each is annotated with its label, or with PATHS the labels of its
ancestors and its own."
  (let ((terms (orgsyndb--vocabulary root name)))
    (orgsyndb--candidates
     (mapcar (lambda (entry) (symbol-name (car entry))) terms)
     (mapcar (lambda (entry)
               (cons (symbol-name (car entry))
                     (if paths
                         (orgsyndb--term-path terms (car entry))
                       (alist-get 'label (cdr entry)))))
             terms))))

(defun orgsyndb--in-use (root keys)
  "Return the distinct strings that the procedures of ROOT other than
the current buffer's list under KEYS, symbols."
  (let (found)
    (dolist (record (orgsyndb-procedures root))
      (let ((front-matter
             (and (not (equal (expand-file-name (alist-get 'path record) root)
                              buffer-file-name))
                  (alist-get 'front_matter record))))
        (dolist (key keys)
          (let ((value (alist-get key front-matter)))
            (dolist (item (if (listp value) value (list value)))
              (when (stringp item)
                (push item found)))))))
    (sort (delete-dups found) #'string<)))

(defun orgsyndb--procedure-ids (root language)
  "Return the procedure IDs of ROOT, each annotated with the title of
the file that a file in LANGUAGE refers to."
  (let ((ids (sort (delete-dups (mapcar (lambda (entry)
                                          (alist-get 'id entry))
                                        (orgsyndb-procedures root)))
                   #'string<)))
    (orgsyndb--candidates
     ids
     (mapcar (lambda (id)
               (cons id (alist-get 'title
                                   (alist-get 'front_matter
                                              (orgsyndb--definition
                                               root id language)))))
             ids))))

(defun orgsyndb--entry-candidates (root id language)
  "Return the entry numbers of the general procedure ID of ROOT, each
annotated with the compound keys of that entry's products."
  (let* ((record (orgsyndb--definition root id language))
         (scope (alist-get 'scope (alist-get 'front_matter record)))
         (number 0)
         numbers annotations)
    (when (listp scope)
      (dolist (entry scope)
        (let ((label (number-to-string (cl-incf number))))
          (push label numbers)
          (push (cons label
                      (mapconcat (lambda (product)
                                   (or (alist-get 'compound product) "?"))
                                 (alist-get 'products entry) ", "))
                annotations))))
    (and numbers (orgsyndb--candidates (nreverse numbers) annotations))))

(defun orgsyndb--value-candidates (root entity key)
  "Return the candidates for a string value of KEY, a string, in a file
of ENTITY, `procedure', `sequence' or `compound', of ROOT, or nil."
  (let ((language (orgsyndb--language-code buffer-file-name)))
    (pcase (cons entity key)
      (`(procedure . "status")
       (orgsyndb--candidates (orgsyndb--schema root 'procedure 'statuses)))
      (`(procedure . "language")
       (orgsyndb--candidates (orgsyndb--schema root 'procedure 'languages)))
      (`(procedure . "reaction_types")
       (orgsyndb--vocabulary-candidates root "reaction-types"))
      (`(procedure . "tags")
       (orgsyndb--candidates (orgsyndb--in-use root '(tags))))
      (`(procedure . ,(or "authors" "checked_by"))
       (orgsyndb--candidates (orgsyndb--in-use root '(authors checked_by))))
      (`(procedure . ,(or "substrates" "compound"))
       (orgsyndb--compound-candidates root))
      (`(sequence . "target") (orgsyndb--compound-candidates root))
      (`(sequence . "procedure") (orgsyndb--procedure-ids root language))
      (`(,(or 'procedure 'compound) . ,(or "scheme_image" "structure_image"))
       (orgsyndb--candidates (orgsyndb--structure-images root)))
      (`(,(or 'procedure 'compound) . ,_)
       (let ((field (orgsyndb--declaration root entity key)))
         (and field (equal (alist-get 'type field) "choice")
              (orgsyndb--vocabulary-candidates
               root (alist-get 'vocabulary field) t)))))))

(defun orgsyndb--boolean-p (root entity key)
  "Return non-nil when KEY is a declared boolean field of ENTITY in ROOT."
  (and (memq entity '(procedure compound))
       (equal (alist-get 'type (orgsyndb--declaration root entity key))
              "boolean")))

(defun orgsyndb--key-candidates (root entity set)
  "Return the top-level keys of a file of ENTITY in ROOT that SET, a
list of strings, does not hold yet, annotated with `required' or the
declared field's label."
  (let* ((required (pcase entity
                     ('procedure (orgsyndb--schema root 'procedure 'required))
                     ('compound (orgsyndb--schema root 'compound 'required))))
         (keys (pcase entity
                 ('procedure
                  (append required
                          (orgsyndb--schema root 'procedure 'optional)))
                 ('compound
                  (append required
                          (orgsyndb--schema root 'compound 'optional)))
                 ('sequence (orgsyndb--schema root 'sequence 'keys))))
         (declared (and (memq entity '(procedure compound))
                        (orgsyndb--declarations root entity)))
         annotations)
    (dolist (key required)
      (push (cons key "required") annotations))
    (dolist (field declared)
      (push (cons (alist-get 'key field) (alist-get 'label field))
            annotations))
    (orgsyndb--candidates
     (cl-remove-if (lambda (key) (member key set))
                   (delete-dups
                    (append keys (mapcar (lambda (field)
                                           (alist-get 'key field))
                                         declared))))
     annotations)))

(defun orgsyndb--capf (start end data)
  "Return the completion-at-point answer for START, END and DATA, the
\(CANDIDATES . ANNOTATE) that a candidates function gives, or nil."
  (when (car data)
    (append (list start end (car data))
            (and (cdr data) (list :annotation-function (cdr data)))
            (list :exclusive 'no))))

;;;; TOML front matter and compound files

(defun orgsyndb--front-matter-bounds ()
  "Return (BEG . END) of the buffer's `+++' front matter, or nil.
BEG is the start of the line after the opening delimiter and END the
start of the closing one, or the end of the buffer."
  (save-excursion
    (goto-char (point-min))
    (when (looking-at "\\+\\+\\+[ \t\r]*$")
      (forward-line 1)
      (let ((beg (point)))
        (cons beg (if (re-search-forward "^\\+\\+\\+[ \t\r]*$" nil t)
                      (match-beginning 0)
                    (point-max)))))))

(defun orgsyndb--keys-set (beg end)
  "Return the top-level keys that the TOML text from BEG to END sets."
  (let (keys)
    (save-excursion
      (goto-char beg)
      (while (re-search-forward "^\\([A-Za-z0-9_-]+\\)[ \t]*=" end t)
        (push (match-string-no-properties 1) keys)))
    keys))

(cl-defstruct (orgsyndb--frame (:constructor orgsyndb--frame
                                             (type open &optional key)))
  "An open table or array of TOML text being read."
  type open key value)

(defun orgsyndb--toml-context (beg)
  "Describe what point is in, in the TOML text that starts at BEG.
Return one of:
- (key START): a key being written at the start of a line, from START;
- (string KEY START END OPEN): the inside of a double-quoted string,
  from START to END, that is the value or an array entry of KEY, the
  innermost key whose value encloses it; OPEN is where the innermost
  enclosing table begins;
- (bare KEY START OPEN): a bare value of KEY being written from START;
- nil for anything else."
  (let ((pos (point))
        (stack (list (orgsyndb--frame 'table beg)))
        (in-string nil)
        (string-start nil)
        (case-fold-search nil))
    (save-excursion
      (goto-char beg)
      (while (< (point) pos)
        (let ((char (char-after))
              (frame (car stack)))
          (cond
           (in-string
            (cond ((eq char ?\\) (forward-char 1))
                  ((memq char '(?\" ?\n)) (setq in-string nil)))
            (forward-char 1))
           ((eq char ?\")
            (setq in-string t
                  string-start (1+ (point)))
            (forward-char 1))
           ((eq char ?#)
            (skip-chars-forward "^\n" pos))
           ((eq char ?\n)
            (unless (cdr stack)
              (setf (orgsyndb--frame-key frame) nil
                    (orgsyndb--frame-value frame) nil))
            (forward-char 1))
           ((and (eq char ?\[) (null (cdr stack))
                 (null (orgsyndb--frame-key frame)))
            ;; A table header such as [table] or [[table]].
            (skip-chars-forward "^\n" pos))
           ((eq char ?\[)
            (push (orgsyndb--frame 'array (point)
                                   (orgsyndb--frame-key frame))
                  stack)
            (forward-char 1))
           ((eq char ?{)
            (push (orgsyndb--frame 'table (point)) stack)
            (forward-char 1))
           ((memq char '(?\] ?}))
            (when (cdr stack)
              (pop stack))
            (forward-char 1))
           ((and (eq char ?,) (eq (orgsyndb--frame-type frame) 'table))
            (setf (orgsyndb--frame-key frame) nil
                  (orgsyndb--frame-value frame) nil)
            (forward-char 1))
           ((and (eq (orgsyndb--frame-type frame) 'table)
                 (null (orgsyndb--frame-key frame))
                 (looking-at "\\([A-Za-z0-9_-]+\\)[ \t]*=")
                 (<= (match-end 0) pos))
            (setf (orgsyndb--frame-key frame) (match-string-no-properties 1)
                  (orgsyndb--frame-value frame) (match-end 0))
            (goto-char (match-end 0)))
           (t (forward-char 1)))))
      (let* ((frame (car stack))
             (open (orgsyndb--frame-open
                    (cl-find 'table stack :key #'orgsyndb--frame-type))))
        (cond
         (in-string
          (and (orgsyndb--frame-key frame)
               (list 'string (orgsyndb--frame-key frame) string-start
                     (save-excursion (skip-chars-forward "^\"\n") (point))
                     open)))
         ((and (eq (orgsyndb--frame-type frame) 'table)
               (orgsyndb--frame-value frame))
          (let ((text (buffer-substring-no-properties
                       (orgsyndb--frame-value frame) pos)))
            (and (string-match "\\`[ \t]*\\([A-Za-z0-9]*\\)\\'" text)
                 (list 'bare (orgsyndb--frame-key frame)
                       (- pos (length (match-string 1 text)))
                       open))))
         ((and (null (cdr stack)) (null (orgsyndb--frame-key frame)))
          (let ((line-start (line-beginning-position)))
            (and (string-match-p "\\`[A-Za-z0-9_]*\\'"
                                 (buffer-substring-no-properties line-start
                                                                 pos))
                 (looking-at-p "[A-Za-z0-9_]*[ \t]*$")
                 (list 'key line-start)))))))))

(defun orgsyndb--step-procedure (open)
  "Return the procedure ID that the inline table at OPEN names, or nil."
  (save-excursion
    (goto-char open)
    (let ((end (save-excursion
                 (or (search-forward "}" (line-end-position) t)
                     (line-end-position)))))
      (and (re-search-forward "procedure[ \t]*=[ \t]*\"\\([^\"]*\\)\"" end t)
           (match-string-no-properties 1)))))

(defun orgsyndb--complete-toml (entity beg end)
  "Complete at point in TOML text of ENTITY from BEG to END."
  (when (and (<= beg (point)) (<= (point) end))
    (let ((root orgsyndb--root)
          (language (orgsyndb--language-code buffer-file-name)))
      (pcase (orgsyndb--toml-context beg)
        (`(key ,start)
         (orgsyndb--capf start (point)
                         (orgsyndb--key-candidates
                          root entity (orgsyndb--keys-set beg end))))
        (`(string ,key ,start ,stop ,_open)
         (orgsyndb--capf start stop
                         (orgsyndb--value-candidates root entity key)))
        (`(bare ,key ,start ,open)
         (cond
          ((orgsyndb--boolean-p root entity key)
           (orgsyndb--capf start (point)
                           (orgsyndb--candidates '("true" "false"))))
          ((and (eq entity 'sequence) (equal key "entry"))
           (let ((id (orgsyndb--step-procedure open)))
             (and id (orgsyndb--capf start (point)
                                     (orgsyndb--entry-candidates
                                      root id language)))))))))))

;;;; Org sources

(defconst orgsyndb--org-withheld-keys
  '("title" "slug" "tags" "date" "lastmod" "ai_model" "scope")
  "The procedure keys that an Org source writes with keywords or its
scope table rather than as custom front matter.")

(defun orgsyndb--org-custom-keys (root)
  "Return the custom front-matter keys of an Org source of ROOT that its
custom front matter does not set yet, each with its leading colon."
  (let* ((text (buffer-substring-no-properties (point-min) (point-max)))
         (set (osdb-org--custom-front-matter-keys
               (cdr (assoc "HUGO_CUSTOM_FRONT_MATTER"
                           (osdb-org-keywords text)))))
         (data (orgsyndb--key-candidates root 'procedure set))
         (keys (cons "id" (cl-remove-if (lambda (key)
                                          (member key
                                                  orgsyndb--org-withheld-keys))
                                        (car data))))
         (annotate (cdr data)))
    (cons (mapcar (lambda (key) (concat ":" key))
                  (cl-remove-if (lambda (key) (member key set)) keys))
          (lambda (candidate)
            (funcall annotate (string-remove-prefix ":" candidate))))))

(defun orgsyndb--complete-org-custom (root value-start)
  "Complete at point on a custom front-matter line whose value starts at
VALUE-START."
  (let ((pos (point))
        (depth 0)
        (in-string nil)
        (string-start nil)
        (key nil))
    (save-excursion
      (goto-char value-start)
      (while (< (point) pos)
        (let ((char (char-after)))
          (cond
           (in-string
            (cond ((eq char ?\\) (forward-char 1))
                  ((eq char ?\") (setq in-string nil))))
           ((eq char ?\") (setq in-string t string-start (1+ (point))))
           ((eq char ?\() (cl-incf depth))
           ((eq char ?\)) (setq depth (max 0 (1- depth))))
           ((and (eq char ?:) (= depth 0)
                 (or (= (point) value-start)
                     (memq (char-before) '(?\s ?\t)))
                 (looking-at ":\\([A-Za-z0-9_]+\\)"))
            (setq key (match-string-no-properties 1))))
          (forward-char 1))))
    (let ((before (buffer-substring-no-properties value-start pos)))
      (cond
       (in-string
        (and key
             (orgsyndb--capf string-start
                             (save-excursion (skip-chars-forward "^\"\n")
                                             (point))
                             (if (equal key "products")
                                 (orgsyndb--compound-candidates root)
                               (orgsyndb--value-candidates root 'procedure
                                                           key)))))
       ((/= depth 0) nil)
       ((string-match "\\(?:\\`\\|[ \t]\\)\\(:[A-Za-z0-9_]*\\)\\'" before)
        (orgsyndb--capf (- pos (length (match-string 1 before))) pos
                        (orgsyndb--org-custom-keys root)))
       ((and (string-match ":\\([A-Za-z0-9_]+\\)[ \t]+\\([a-z]*\\)\\'" before)
             (orgsyndb--boolean-p root 'procedure (match-string 1 before)))
        (orgsyndb--capf (- pos (length (match-string 2 before))) pos
                        (orgsyndb--candidates '("true" "false"))))))))

(defun orgsyndb--word-start ()
  "Return the start of the word before point, up to a blank or a `|'."
  (save-excursion
    (skip-chars-backward "^ \t|\n")
    (point)))

(defun orgsyndb--complete-scope-cell (root)
  "Complete a compound key in a substrates or products cell of the
table named scope, when point is in one."
  (let ((pos (point))
        (case-fold-search t))
    (save-excursion
      (beginning-of-line)
      (unless (looking-at-p "[ \t]*|-")
        (let ((row (point))
              (column (1- (cl-count ?| (buffer-substring-no-properties
                                        (point) pos)))))
          (while (and (not (bobp))
                      (save-excursion (forward-line -1)
                                      (looking-at-p "[ \t]*|")))
            (forward-line -1))
          (when (and (/= (point) row)
                     (save-excursion
                       (and (zerop (forward-line -1))
                            (looking-at-p
                             "[ \t]*#\\+name:[ \t]*scope[ \t]*$"))))
            (let ((header (osdb-org--table-cells
                           (buffer-substring-no-properties
                            (point) (line-end-position)))))
              (when (member (nth column header) '("substrates" "products"))
                (goto-char pos)
                (orgsyndb--capf (orgsyndb--word-start) pos
                                (orgsyndb--compound-candidates root))))))))))

(defun orgsyndb--complete-org ()
  "Complete at point in an Org source."
  (let ((root orgsyndb--root)
        (case-fold-search t))
    (save-excursion
      (let ((pos (point)))
        (beginning-of-line)
        (cond
         ((looking-at "[ \t]*#\\+hugo_custom_front_matter:[ \t]*")
          (and (<= (match-end 0) pos)
               (let ((value-start (match-end 0)))
                 (goto-char pos)
                 (orgsyndb--complete-org-custom root value-start))))
         ((looking-at "[ \t]*#\\+hugo_tags:")
          (and (< (match-end 0) pos)
               (progn (goto-char pos)
                      (orgsyndb--capf (orgsyndb--word-start) pos
                                      (orgsyndb--candidates
                                       (orgsyndb--in-use root '(tags)))))))
         ((looking-at-p "[ \t]*|")
          (goto-char pos)
          (orgsyndb--complete-scope-cell root)))))))

;;;; Entry points

(defun orgsyndb-completion-at-point ()
  "Complete the key or value at point in a collection file.
In procedures, sequences and compound files it completes front-matter
keys and their values; in Org sources the keys and values of
`#+HUGO_CUSTOM_FRONT_MATTER', the words of `#+HUGO_TAGS' and the
compound keys of the scope table.  Elsewhere it returns nil."
  (when orgsyndb--root
    (condition-case err
        (pcase orgsyndb--kind
          ((or 'md-procedure 'sequence)
           (let ((bounds (orgsyndb--front-matter-bounds)))
             (and bounds
                  (orgsyndb--complete-toml
                   (if (eq orgsyndb--kind 'sequence) 'sequence 'procedure)
                   (car bounds) (cdr bounds)))))
          ('compound
           (orgsyndb--complete-toml 'compound (point-min) (point-max)))
          ('org-procedure (orgsyndb--complete-org)))
      (error (message "orgsyndb: %s" (error-message-string err))
             nil))))

;;;###autoload
(defun orgsyndb-insert-compound ()
  "Insert at point the key of a compound chosen by its name.
The names are German in a file whose language code is `de', where the
compound has one."
  (interactive)
  (let* ((root (orgsyndb--current-root))
         (german (equal (orgsyndb--language-code buffer-file-name) "de"))
         (choices
          (mapcar (lambda (entry)
                    (let* ((key (alist-get 'key entry))
                           (data (alist-get 'data entry))
                           (name (or (and german (alist-get 'name_de data))
                                     (alist-get 'name data)
                                     key)))
                      (list (format "%s (%s)" name key) key
                            (alist-get 'formula data))))
                  (orgsyndb--compounds root)))
         (completion-extra-properties
          (list :annotation-function
                (lambda (candidate)
                  (let ((formula (nth 2 (assoc candidate choices))))
                    (and formula (concat " " formula))))))
         (choice (completing-read "Compound: " choices nil t))
         (key (or (cadr (assoc choice choices))
                  (and (string-match "(\\([a-z0-9-]+\\))\\'" choice)
                       (match-string 1 choice))
                  (user-error "No compound %s" choice))))
    (insert key)))

(provide 'orgsyndb-complete)

;;; orgsyndb-complete.el ends here

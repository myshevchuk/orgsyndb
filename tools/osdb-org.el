;;; osdb-org.el --- Org front end of the OrgSynDB export  -*- lexical-binding: t; -*-

;;; Commentary:

;; Reads the Org procedure sources of a directory and decides what the
;; export does with them: which entries are sources, which problems they
;; have, the `date', `lastmod' and `ai_model' each source is exported
;; with, and the `scope' its table named scope gives.  tools/export.el loads this file; tests/el/osdb-org-tests.el
;; tests it.
;;
;; Loading it defines functions and constants and does nothing else.  It
;; needs neither Org nor ox-hugo nor tomelr, and reads Org text with its
;; own line scanner.
;;
;; A problem is a list (FIELD SEVERITY MESSAGE) of three strings, with
;; SEVERITY "error" or "warning".  An instant is an integer, seconds
;; since the epoch.  Functions that take an optional ZONE default it to
;; `osdb-org-zone'; it is always passed explicitly to the time functions,
;; so that the result does not depend on the TZ environment variable.

;;; Code:

(require 'cl-lib)
(require 'subr-x)
(require 'time-date)

(defconst osdb-org-zone "Europe/Berlin"
  "The time zone of the timestamps in an Org source.")

(defconst osdb-org-languages '("de" "en")
  "The language codes a procedure file name may carry.")

(defconst osdb-org-weekdays ["Sun" "Mon" "Tue" "Wed" "Thu" "Fri" "Sat"]
  "English weekday abbreviations, indexed by `decode-time' day of week.")

(defconst osdb-org-form "[YYYY-MM-DD Day hh:mm:ss]"
  "The form of a timestamp keyword, as the messages show it.")

(defconst osdb-org-timestamp-regexp
  (concat "\\`\\([[<]\\)\\([0-9]\\{4\\}\\)-\\([0-9]\\{2\\}\\)-"
          "\\([0-9]\\{2\\}\\) \\([^] \t>]+\\) \\([0-9]\\{2\\}\\):"
          "\\([0-9]\\{2\\}\\):\\([0-9]\\{2\\}\\)\\([]>]\\)\\'")
  "A timestamp: bracket, date, weekday, time and bracket as groups 1-9.")

(defconst osdb-org-ai-model-regexp "\\`[A-Za-z0-9][A-Za-z0-9._:/@+-]*\\'"
  "A model identifier, as `#+AI_MODEL' names it.")

(defconst osdb-org-file-name-regexp
  (concat "\\`\\(OSDB-[0-9]\\{4\\}\\)-[a-z0-9]+\\(?:-[a-z0-9]+\\)*"
          "\\(?:\\.\\([a-z]\\{2\\}\\)\\)?\\.org\\'")
  "An Org procedure file name: ID as group 1, language code as group 2.")

(defconst osdb-org-file-keywords '("CREATED" "LAST_MODIFIED" "AI_MODEL")
  "The file-level keywords a source carries at most once, in check order.
All but `AI_MODEL' are required.")

(defconst osdb-org-forbidden-keywords
  '("DATE" "HUGO_LASTMOD" "HUGO_AUTO_SET_LASTMOD"
    "HUGO_FRONT_MATTER_KEY_REPLACE" "EXPORT_FILE_NAME" "HUGO_BASE_DIR"
    "HUGO_BASE_CONTENT_FOLDER" "HUGO_SECTION" "HUGO_BUNDLE" "SETUPFILE"
    "INCLUDE")
  "Keywords by which ox-hugo would set an exported value, in report order.")

(defconst osdb-org-front-matter-keys
  '(("date" . "#+CREATED")
    ("lastmod" . "#+LAST_MODIFIED")
    ("ai_model" . "#+AI_MODEL"))
  "Custom front-matter keys the export writes, with their keyword.")

(defconst osdb-org-scope-columns
  '("substrates" "products" "yield_percent" "scale" "time" "temperature"
    "note")
  "The columns of a scope table, in the order an entry writes its keys.
The first three are required.")

(defconst osdb-org-number-regexp "\\`-?[0-9]+\\(?:[.,][0-9]+\\)?\\'"
  "A number in a scope table cell, with a decimal point or comma.")

(defconst osdb-org-routes-message
  "the export sets date, lastmod, ai_model and the export file name itself"
  "The reason given for every forbidden route but custom front matter.")

;;;; Problems

(defun osdb-org--error (field message)
  "Return an error problem on FIELD with MESSAGE."
  (list field "error" message))

(defun osdb-org--warning (field message)
  "Return a warning problem on FIELD with MESSAGE."
  (list field "warning" message))

(defun osdb-org--problem-p (value)
  "Return non-nil when VALUE is a problem rather than a list of instants."
  (stringp (car-safe value)))

(defun osdb-org-problem-line (path problem)
  "Return the report line of PROBLEM on the file PATH.
The line is PATH:FIELD: SEVERITY: MESSAGE, without a newline."
  (pcase-let ((`(,field ,severity ,message) problem))
    (format "%s:%s: %s: %s" path field severity message)))

;;;; Lines and keywords

(defun osdb-org--outside-lines (text &optional openers)
  "Return the lines of TEXT that are outside blocks, in order.
Lines end at LF, and a CR before the LF is dropped.  A line beginning,
after spaces or tabs, with `#+begin_' in any case opens a block that
runs to the next line beginning the same way with `#+end_'; neither
those two lines nor any line between them is returned, except that
the opening lines are returned too when OPENERS is non-nil."
  (let ((case-fold-search nil)
        (in-block nil)
        (found nil))
    (dolist (line (split-string text "\n"))
      (setq line (string-remove-suffix "\r" line))
      (cond
       (in-block
        (setq in-block
              (not (string-match-p "\\`[ \t]*#\\+[Ee][Nn][Dd]_" line))))
       ((string-match-p "\\`[ \t]*#\\+[Bb][Ee][Gg][Ii][Nn]_" line)
        (setq in-block t)
        (when openers
          (push line found)))
       (t (push line found))))
    (nreverse found)))

(defun osdb-org--keywords-of-lines (lines)
  "Return the keywords of LINES as `osdb-org-keywords' does."
  (let ((case-fold-search nil)
        (found nil))
    (dolist (line lines)
      (when (string-match "\\`[ \t]*#\\+\\([A-Za-z_]+\\):\\(.*\\)\\'" line)
        (let* ((name (upcase (match-string 1 line)))
               (value (string-trim (match-string 2 line)
                                   "[ \t\r]+" "[ \t\r]+"))
               (entry (assoc name found)))
          (if entry
              (push value (cdr entry))
            (push (list name value) found)))))
    (nreverse (mapcar (lambda (entry)
                        (cons (car entry) (reverse (cdr entry))))
                      found))))

(defun osdb-org-keywords (text)
  "Return the file-level keywords of the Org TEXT.
The result is an alist of (NAME . VALUES), in order of first
appearance.  NAME is the keyword name in upper case, and VALUES are its
values in file order, trimmed of spaces, tabs and CRs.  A keyword line
is optional spaces or tabs, `#+', a name of ASCII letters and
underscores, `:' and the value.  Lines inside blocks are skipped, as
`osdb-org--outside-lines' defines them."
  (osdb-org--keywords-of-lines (osdb-org--outside-lines text)))

;;;; Time

(defun osdb-org--utc-seconds (year month day hour minute second)
  "Return the instant of a wall-clock time read as UTC.
The time is given by YEAR, MONTH, DAY, HOUR, MINUTE and SECOND."
  (time-convert (encode-time (list second minute hour day month year
                                   nil nil 0))
                'integer))

(defun osdb-org--offset (instant zone)
  "Return the UTC offset of ZONE at INSTANT, in seconds."
  (nth 8 (decode-time instant zone)))

(defun osdb-org-zone-available-p (&optional zone)
  "Return non-nil when the tz database knows ZONE as Europe/Berlin's rules.
That is, when ZONE's UTC offsets at 2026-01-15T12:00:00Z and
2026-07-15T12:00:00Z are 3600 and 7200 seconds.  An unknown zone name
reads as UTC and fails the check."
  (let ((zone (or zone osdb-org-zone)))
    (and (eql (osdb-org--offset (osdb-org--utc-seconds 2026 1 15 12 0 0)
                                zone)
              3600)
         (eql (osdb-org--offset (osdb-org--utc-seconds 2026 7 15 12 0 0)
                                zone)
              7200))))

(defun osdb-org-local-instants (year month day hour minute second
                                     &optional zone)
  "Return the instants that a wall-clock time names in ZONE.
The time is given by YEAR, MONTH, DAY, HOUR, MINUTE and SECOND.  The
result is sorted, earliest first: empty for a time skipped by a forward
clock change, two instants for a time repeated by a backward change,
and one otherwise.  It assumes that no two clock changes of ZONE fall
within two days of each other."
  (let* ((zone (or zone osdb-org-zone))
         (wall (osdb-org--utc-seconds year month day hour minute second))
         (fields (list second minute hour day month year))
         (found nil))
    ;; The offsets a day before and after are the only candidates.
    (dolist (offset (delete-dups
                     (list (osdb-org--offset (- wall 86400) zone)
                           (osdb-org--offset (+ wall 86400) zone))))
      (let* ((instant (- wall offset))
             (decoded (decode-time instant zone)))
        (when (and (eql (nth 8 decoded) offset)
                   (equal (take 6 decoded) fields))
          (push instant found))))
    (sort found #'<)))

(defun osdb-org-export-instants (created last-modified)
  "Choose the exported `date' and `lastmod' from named instants.
CREATED and LAST-MODIFIED are non-empty lists of instants.  Return
\(DATE . LASTMOD): DATE is the earliest of CREATED, and LASTMOD the
earliest of LAST-MODIFIED that is not before DATE, or the latest of
LAST-MODIFIED when there is none."
  (let* ((date (apply #'min created))
         (later (cl-remove-if (lambda (instant) (< instant date))
                              last-modified)))
    (cons date (if later
                   (apply #'min later)
                 (apply #'max last-modified)))))

(defun osdb-org-rfc3339 (instant &optional zone)
  "Return INSTANT as YYYY-MM-DDThh:mm:ss+HH:MM in ZONE."
  (format-time-string "%Y-%m-%dT%H:%M:%S%:z" instant (or zone osdb-org-zone)))

(defun osdb-org-parse-timestamp (field value &optional zone)
  "Parse VALUE, the timestamp of the keyword FIELD, in ZONE.
Return the instants it names, earliest first, or the first problem
found, an error on FIELD.  The checks run in this order: form,
inactive brackets, date, time, weekday, existence in ZONE."
  (let ((zone (or zone osdb-org-zone))
        (case-fold-search nil))
    (if (or (not (string-match osdb-org-timestamp-regexp value))
            (not (eq (equal (match-string 1 value) "[")
                     (equal (match-string 9 value) "]"))))
        (osdb-org--error field (format "\"%s\" must have the form %s"
                                       value osdb-org-form))
      (pcase-let ((`(,year ,month ,day ,hour ,minute ,second)
                   (mapcar (lambda (group)
                             (string-to-number (match-string group value)))
                           '(2 3 4 6 7 8)))
                  (weekday (match-string 5 value)))
        (cond
         ((equal (match-string 1 value) "<")
          (osdb-org--error
           field (format "\"%s\" must be an inactive timestamp in square \
brackets, %s" value osdb-org-form)))
         ((not (and (<= 1 year 9999) (<= 1 month 12)
                    (<= 1 day (date-days-in-month year month))))
          (osdb-org--error field (format "\"%s\" is not a valid date"
                                         value)))
         ((not (and (< hour 24) (< minute 60) (< second 60)))
          (osdb-org--error field (format "\"%s\" is not a valid time"
                                         value)))
         (t
          (let ((expected
                 (aref osdb-org-weekdays
                       (nth 6 (decode-time
                               (osdb-org--utc-seconds year month day 0 0 0)
                               0)))))
            (if (not (equal weekday expected))
                (osdb-org--error
                 field (format "weekday \"%s\" does not match \
%04d-%02d-%02d (%s)" weekday year month day expected))
              (or (osdb-org-local-instants year month day hour minute
                                           second zone)
                  (osdb-org--error
                   field (format "\"%s\" does not exist in Europe/Berlin \
\(skipped by the clock change)" value)))))))))))

;;;; Forbidden routes to the exported values

(defun osdb-org--balanced-split (text)
  "Split TEXT where ox-hugo splits custom front matter into arguments.
This is `org-babel-balanced-split' with the separator `[ \\t]:': the
text splits at each `:' after a space or tab, outside balanced brackets
and double-quoted strings, and the space or tab before it is dropped.
An unbalanced bracket and an unclosed quote are ordinary characters.
Return the pieces, without the separators, in order."
  (let ((index 0)
        (length (length text))
        (partial nil)
        (result nil))
    (while (< index length)
      (let ((char (aref text index))
            (past (and (> index 0) (aref text (1- index)))))
        (cond
         ((and (memq past '(?\s ?\t)) (eq char ?:))
          (pop partial)
          (when partial
            (push (apply #'string (nreverse partial)) result)
            (setq partial nil))
          (setq index (1+ index)))
         ((memq char '(?\( ?\[))
          ;; Everything up to the balancing bracket is one unit; an
          ;; unbalanced bracket is an ordinary character.  As in Org,
          ;; only `(' opens a nested bracket.
          (let ((end (1+ index))
                (openings (list char)))
            (while (and openings (< end length))
              (pcase (aref text end)
                (?\( (push ?\( openings))
                (?\] (when (eq (car openings) ?\[) (pop openings)))
                (?\) (when (eq (car openings) ?\() (pop openings))))
              (setq end (1+ end)))
            (if openings
                (setq partial (cons char partial)
                      index (1+ index))
              (setq partial (nconc (nreverse (string-to-list
                                              (substring text index end)))
                                   partial)
                    index end))))
         ((and (eq char ?\") (not (eq past ?\\)))
          ;; Up to the next double quote not preceded by a backslash,
          ;; where the opening quote itself counts as such a character.
          (let ((end (cl-loop for at from index below (1- length)
                              when (and (not (eq (aref text at) ?\\))
                                        (eq (aref text (1+ at)) ?\"))
                              return (+ at 2))))
            (if end
                (setq partial (nconc (nreverse (string-to-list
                                                (substring text index end)))
                                     partial)
                      index end)
              (setq partial (cons char partial)
                    index (1+ index)))))
         (t (setq partial (cons char partial)
                  index (1+ index))))))
    (when partial
      (push (apply #'string (nreverse partial)) result))
    (nreverse result)))

(defun osdb-org--front-matter-key (piece)
  "Return the key of the argument PIECE, without its leading `:'.
As `org-babel-parse-header-arguments' does, the key is the first word
of PIECE when a value follows it, and otherwise PIECE without trailing
whitespace."
  (let ((case-fold-search nil))
    (string-remove-prefix
     ":" (if (string-match (concat "\\([^ \f\t\n\r\v]+\\)[ \f\t\n\r\v]+"
                                   "[^ \f\t\n\r\v]")
                           piece)
             (match-string 1 piece)
           (replace-regexp-in-string "[ \f\t\n\r\v]+\\'" "" piece)))))

(defun osdb-org--custom-front-matter-keys (values)
  "Return the keys of the custom front matter VALUES, without `:'.
VALUES are the values of the `#+HUGO_CUSTOM_FRONT_MATTER' lines, which
ox-hugo joins with single spaces and splits as `osdb-org--balanced-split'
does.  As in ox-hugo, the first piece names a key whether or not it
begins with `:'."
  (let ((text (string-join values " ")))
    (unless (string-blank-p text)
      (let ((pieces (osdb-org--balanced-split text)))
        (mapcar #'osdb-org--front-matter-key
                (cons (car pieces)
                      (mapcar (lambda (piece) (concat ":" piece))
                              (cdr pieces))))))))

(defun osdb-org--route-name-p (name)
  "Return non-nil when the property NAME could set an exported value.
That is a name starting with EXPORT_ or equal to LOG_INTO_DRAWER, in
any case."
  (let ((name (upcase name)))
    (or (string-prefix-p "EXPORT_" name)
        (equal name "LOG_INTO_DRAWER"))))

(defun osdb-org--route-problems (lines keywords headers)
  "Return the errors for the forbidden routes in an Org source.
LINES are its lines outside blocks, KEYWORDS its keywords, as
`osdb-org-keywords' returns them, and HEADERS its lines outside blocks
together with the lines that open blocks.  The errors follow the order
of the rules: forbidden keywords, custom front-matter keys,
`#+PROPERTY' lines, property drawer lines, logbook drawers and source
block header arguments."
  (let ((case-fold-search nil)
        (problems nil)
        (seen nil))
    (dolist (keyword osdb-org-forbidden-keywords)
      (when (assoc keyword keywords)
        (push (osdb-org--error (concat "#+" keyword)
                               (concat "must not be used; "
                                       osdb-org-routes-message))
              problems)))
    (let ((keys (mapcar #'downcase
                        (osdb-org--custom-front-matter-keys
                         (cdr (assoc "HUGO_CUSTOM_FRONT_MATTER" keywords))))))
      (pcase-dolist (`(,key . ,source) osdb-org-front-matter-keys)
        (when (member key keys)
          (push (osdb-org--error
                 "#+HUGO_CUSTOM_FRONT_MATTER"
                 (format "must not set :%s; the export writes it from %s"
                         key source))
                problems))))
    (dolist (value (cdr (assoc "PROPERTY" keywords)))
      ;; NAME+ appends to the property NAME.
      (when (string-match "\\`\\([^ \t]+?\\)\\+?\\(?:[ \t]\\|\\'\\)" value)
        (let ((name (upcase (match-string 1 value))))
          (when (and (osdb-org--route-name-p name)
                     (not (member name seen)))
            (push name seen)
            (push (osdb-org--error
                   "#+PROPERTY" (format "must not set %s; %s" name
                                        osdb-org-routes-message))
                  problems)))))
    (setq seen nil)
    (dolist (line lines)
      (when (string-match "\\`[ \t]*:\\([^ \t]+?\\)\\+?:\\(?:[ \t].*\\)?\\'"
                          line)
        (let ((name (upcase (match-string 1 line))))
          (when (and (osdb-org--route-name-p name)
                     (not (member name seen)))
            (push name seen)
            (push (osdb-org--error (format ":%s:" name)
                                   (concat "must not be used; "
                                           osdb-org-routes-message))
                  problems)))))
    (when (cl-some (lambda (line)
                     (string-match-p
                      "\\`[ \t]*:[Ll][Oo][Gg][Bb][Oo][Oo][Kk]:[ \t]*\\'" line))
                   lines)
      (push (osdb-org--error ":LOGBOOK:" (concat "must not be used; "
                                                 osdb-org-routes-message))
            problems))
    ;; ox-hugo appends the body of a :front_matter_extra block to the
    ;; front matter; header arguments reach a block from these lines.
    (when (cl-some (lambda (line)
                     (let ((line (downcase line)))
                       (and (string-match-p
                             (concat "\\`[ \t]*\\(?:#\\+\\(?:begin_src"
                                     "\\|header:\\|property:\\)"
                                     "\\|:header-args\\)")
                             line)
                            (string-match-p ":front_matter_extra" line))))
                   headers)
      (push (osdb-org--error ":front_matter_extra"
                             (concat "must not be used; "
                                     osdb-org-routes-message))
            problems))
    (nreverse problems)))

;;;; The scope table

(defun osdb-org--table-cells (line)
  "Return the cells of the Org table row LINE, trimmed, in order."
  (let ((inner (string-remove-prefix "|" (string-trim line))))
    (mapcar #'string-trim
            (split-string (string-remove-suffix "|" inner) "|"))))

(defun osdb-org--scope-tables (text)
  "Return the tables named scope in the Org TEXT, outside blocks, in order.
A table is named scope when the line just before its first row is
`#+NAME: scope', the keyword and the name in any case.  Each element is
\(START END ROWS): START is the index, counted from 0, of the `#+NAME'
line, END the index of the line after the table's last row, and ROWS
the table's lines, without a CR before their LF.  Blocks are those of
`osdb-org--outside-lines'."
  (let ((lines (vconcat (mapcar (lambda (line)
                                  (string-remove-suffix "\r" line))
                                (split-string text "\n"))))
        (index 0)
        (in-block nil)
        (found nil))
    (while (< index (length lines))
      (let ((line (aref lines index))
            (case-fold-search t))
        (cond
         (in-block
          (setq in-block (not (string-match-p "\\`[ \t]*#\\+end_" line))))
         ((string-match-p "\\`[ \t]*#\\+begin_" line)
          (setq in-block t))
         ((and (string-match-p "\\`[ \t]*#\\+name:[ \t]*scope[ \t]*\\'" line)
               (< (1+ index) (length lines))
               (string-match-p "\\`[ \t]*|" (aref lines (1+ index))))
          (let ((end (1+ index)))
            (while (and (< end (length lines))
                        (string-match-p "\\`[ \t]*|" (aref lines end)))
              (setq end (1+ end)))
            (push (list index end
                        (append (substring lines (1+ index) end) nil))
                  found)
            (setq index (1- end))))))
      (setq index (1+ index)))
    (nreverse found)))

(defun osdb-org--scope-number (cell)
  "Return the number the scope table CELL holds, or nil when it holds none.
A decimal comma reads as a decimal point.  A cell without a decimal
part gives an integer."
  (when (string-match-p osdb-org-number-regexp cell)
    (string-to-number (string-replace "," "." cell))))

(defun osdb-org--scope-header-problems (header)
  "Return the problems of the scope table HEADER, a list of column names.
They are, in order: each column outside `osdb-org-scope-columns', each
column named twice, and each required column missing."
  (let* ((names (cl-remove-duplicates header :test #'equal :from-end t))
         (known (lambda (name) (member name osdb-org-scope-columns))))
    (append
     (mapcar (lambda (name)
               (osdb-org--error
                "scope" (format "\"%s\" is not a scope column" name)))
             (cl-remove-if known names))
     (mapcar (lambda (name)
               (osdb-org--error
                "scope" (format "column \"%s\" appears more than once" name)))
             (cl-remove-if-not (lambda (name)
                                 (and (funcall known name)
                                      (> (cl-count name header :test #'equal)
                                         1)))
                               names))
     (mapcar (lambda (name)
               (osdb-org--error "scope" (format "column \"%s\" missing" name)))
             (cl-remove-if (lambda (name) (member name header))
                           (take 3 osdb-org-scope-columns))))))

(defun osdb-org--scope-entry (number header cells)
  "Read the scope table row NUMBER, counted from 1, as an entry.
HEADER names the columns, and CELLS are the row's cells.  Return
\(PROBLEMS . ENTRY): the row's errors, and the entry as an alist of
symbols to values, its keys in `osdb-org-scope-columns' order except
that `products' comes last and `yield_percent' is folded into it.  An
empty cell sets no key; a missing cell is empty."
  (let ((row (cl-mapcar #'cons header
                        (append cells (make-list (length header) ""))))
        (problems nil)
        (entry nil))
    (let ((products (split-string (or (cdr (assoc "products" row)) "")))
          (yields (split-string (or (cdr (assoc "yield_percent" row)) ""))))
      (unless (= (length products) (length yields))
        (push (osdb-org--error "scope" (format "row %d: %d products but %d \
yields" number (length products) (length yields)))
              problems))
      (dolist (column osdb-org-scope-columns)
        (let ((cell (cdr (assoc column row))))
          (pcase column
            ((guard (or (null cell) (string-empty-p cell))))
            ("substrates"
             (push (cons 'substrates (split-string cell)) entry))
            ("products")
            ("yield_percent"
             (dolist (yield yields)
               (unless (osdb-org--scope-number yield)
                 (push (osdb-org--error "scope" (format "row %d: \"%s\" is \
not a number" number yield))
                       problems))))
            ("temperature"
             (if (osdb-org--scope-number cell)
                 (push (cons 'temperature (osdb-org--scope-number cell))
                       entry)
               (push (osdb-org--error "scope" (format "row %d: \"%s\" is \
not a number" number cell))
                     problems)))
            (_ (push (cons (intern column) cell) entry)))))
      (when products
        (push (cons 'products
                    (cl-mapcar (lambda (compound yield)
                                 (list (cons 'compound compound)
                                       (cons 'yield_percent
                                             (and yield
                                                  (osdb-org--scope-number
                                                   yield)))))
                               products
                               (append yields
                                       (make-list (length products) nil))))
              entry)))
    (cons (nreverse problems) (nreverse entry))))

(defun osdb-org-scope (text)
  "Read the table named scope in the Org TEXT.
Return (PROBLEMS ENTRIES START END).  PROBLEMS are errors on the field
`scope', in the order of the rules of the scope table.  ENTRIES are the
entries of `scope', each an alist as `osdb-org--scope-entry' returns it,
or nil when there is a problem or no such table.  START is the index of
the table's `#+NAME' line and END that of the line after its last row,
counted from 0 as `osdb-org--scope-tables' counts them; both are nil
when TEXT has no table named scope.  Only the first such table is read;
a second is a problem.  The first row of the table names the columns,
and every further row that is not a separator line is an entry."
  (let ((tables (osdb-org--scope-tables text)))
    (if (null tables)
        (list nil nil nil nil)
      (pcase-let* ((`(,start ,end ,lines) (car tables))
                   (rows (cl-remove-if
                          (lambda (line)
                            (string-match-p "\\`[ \t]*|-" line))
                          lines))
                   (header (and rows (osdb-org--table-cells (car rows))))
                   (problems (append
                              (when (cdr tables)
                                (list (osdb-org--error
                                       "scope" "appears more than once")))
                              (osdb-org--scope-header-problems header)))
                   (entries nil))
        (unless problems
          (cl-loop for cells in (mapcar #'osdb-org--table-cells (cdr rows))
                   for number from 1
                   do (pcase-let ((`(,found . ,entry)
                                   (osdb-org--scope-entry
                                    number header cells)))
                        (setq problems (append problems found))
                        (push entry entries))))
        (list problems (unless problems (nreverse entries)) start end)))))

;;;; One source

(defun osdb-org-check-file-name (name)
  "Return the problems of the Org procedure file NAME, a list.
NAME must be OSDB-NNNN-slug.org, optionally with a known language code
before the suffix."
  (let ((case-fold-search nil))
    (cond
     ((not (string-match osdb-org-file-name-regexp name))
      (list (osdb-org--error
             "file_name" "must be named OSDB-NNNN-short-slug.org, e.g. \
OSDB-0001-ethyl-acetate.org, or OSDB-0001-ethyl-acetate.de.org with a \
language")))
     ((and (match-string 2 name)
           (not (member (match-string 2 name) osdb-org-languages)))
      (list (osdb-org--error
             "file_name" (format "unknown language code \".%s\"; use %s, \
or none" (match-string 2 name) (string-join osdb-org-languages " or "))))))))

(defun osdb-org-lint (text &optional zone)
  "Check the file-level keywords and forbidden routes of the Org TEXT.
Timestamps are read in ZONE.  Return (PROBLEMS CREATED LAST-MODIFIED
AI-MODEL).  PROBLEMS come in the order `#+CREATED', `#+LAST_MODIFIED',
`#+AI_MODEL', ordering, forbidden routes.  CREATED and LAST-MODIFIED are
the instants each timestamp names, and AI-MODEL the value of
`#+AI_MODEL'; each is nil when its keyword is missing or invalid.
`#+AI_MODEL' is optional."
  (let* ((zone (or zone osdb-org-zone))
         (lines (osdb-org--outside-lines text))
         (keywords (osdb-org--keywords-of-lines lines))
         (case-fold-search nil)
         (problems nil)
         (values nil))
    (dolist (keyword osdb-org-file-keywords)
      (let ((field (concat "#+" keyword))
            (given (cdr (assoc keyword keywords))))
        (cond
         ((and (null given) (equal keyword "AI_MODEL")))
         ((null given)
          (push (osdb-org--error field "keyword missing") problems))
         ((cdr given)
          (push (osdb-org--error field "appears more than once") problems))
         ((equal keyword "AI_MODEL")
          (if (or (equal (car given) "none")
                  (string-match-p osdb-org-ai-model-regexp (car given)))
              (push (cons keyword (car given)) values)
            (push (osdb-org--error field "must be a model identifier or none")
                  problems)))
         (t
          (let ((parsed (osdb-org-parse-timestamp field (car given) zone)))
            (if (osdb-org--problem-p parsed)
                (push parsed problems)
              (push (cons keyword parsed) values)))))))
    (let ((created (cdr (assoc "CREATED" values)))
          (last-modified (cdr (assoc "LAST_MODIFIED" values))))
      ;; Earliest possible creation against latest possible modification.
      (when (and created last-modified
                 (> (car created) (car (last last-modified))))
        (push (osdb-org--error "#+LAST_MODIFIED" "is earlier than #+CREATED")
              problems))
      (list (append (nreverse problems)
                    (osdb-org--route-problems
                     lines keywords (osdb-org--outside-lines text t)))
            created last-modified (cdr (assoc "AI_MODEL" values))))))

(defun osdb-org--read (file)
  "Return the text of FILE, or a `front_matter' error.
FILE is decoded as UTF-8, and a leading byte-order mark is dropped.
Line ends are left as they are."
  (condition-case err
      (let ((text (with-temp-buffer
                    (set-buffer-multibyte nil)
                    (insert-file-contents-literally file)
                    (decode-coding-string (buffer-string) 'utf-8-unix))))
        ;; Invalid UTF-8 decodes to raw bytes, above the Unicode range.
        (if (cl-some (lambda (char)
                       (or (<= #xd800 char #xdfff) (> char #x10ffff)))
                     text)
            (osdb-org--error "front_matter" "file is not valid UTF-8")
          (string-remove-prefix "\ufeff" text)))
    (file-error
     (osdb-org--error "front_matter"
                      (format "cannot read file: %s" (nth 2 err))))))

(defun osdb-org--examine-source (path file zone)
  "Examine the Org source FILE, reported as PATH, in ZONE.
Return (PROBLEMS . SOURCE): the problems as (PATH . PROBLEM) pairs, and
the source plist of `osdb-org-examine', or nil when there is a problem."
  (let ((text (osdb-org--read file))
        (name (file-name-nondirectory file)))
    (if (osdb-org--problem-p text)
        (list (list (cons path text)))
      (pcase-let* ((`(,lint ,created ,last-modified ,ai-model)
                    (osdb-org-lint text zone))
                   (problems (append (osdb-org-check-file-name name) lint
                                     (car (osdb-org-scope text)))))
        (if problems
            (list (mapcar (lambda (problem) (cons path problem)) problems))
          (let ((chosen (osdb-org-export-instants created last-modified)))
            (cons nil
                  (list :path file
                        :stem (string-remove-suffix ".org" name)
                        :date (osdb-org-rfc3339 (car chosen) zone)
                        :lastmod (osdb-org-rfc3339 (cdr chosen) zone)
                        :ai-model (unless (equal ai-model "none")
                                    ai-model)))))))))

;;;; A directory of sources

(defun osdb-org-examine (root &optional zone)
  "Examine the top-level entries of the Org directory ROOT in ZONE.
Return (SOURCES . PROBLEMS).

SOURCES holds one plist (:path :stem :date :lastmod :ai-model) per Org
source without any problem, in name order.  :path is absolute, :stem
the file name without `.org', :date and :lastmod are RFC 3339 strings
from `osdb-org-rfc3339', and :ai-model is nil when `#+AI_MODEL' is
absent or `none'.

PROBLEMS holds (PATH . PROBLEM) pairs, sorted by PATH and otherwise in
check order.  PATH is ROOT as given joined with the entry name.  A
subdirectory is an error, a non-directory entry beginning with `.' and
`_index.md' are skipped, an entry ending in `.org' is a source, and any
other entry is a warning."
  (let ((zone (or zone osdb-org-zone))
        (sources nil)
        (problems nil))
    (dolist (name (directory-files root nil
                                   directory-files-no-dot-files-regexp))
      (let ((path (file-name-concat root name))
            (file (expand-file-name name root)))
        (cond
         ((file-directory-p file)
          (push (cons path (osdb-org--error
                            "file_name" "subdirectories are not supported; \
move its files to the top level"))
                problems))
         ((or (string-prefix-p "." name) (equal name "_index.md")))
         ((not (string-suffix-p ".org" name))
          (push (cons path (osdb-org--warning
                            "file_name" "not a procedure file; ignored"))
                problems))
         (t
          (pcase-let ((`(,found . ,source)
                       (osdb-org--examine-source path file zone)))
            (setq problems (append (reverse found) problems))
            (when source
              (push source sources)))))))
    (cons (nreverse sources)
          (sort (nreverse problems)
                (lambda (a b) (string< (car a) (car b)))))))

(provide 'osdb-org)

;;; osdb-org.el ends here

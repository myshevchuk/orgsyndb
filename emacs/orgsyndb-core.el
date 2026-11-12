;;; orgsyndb-core.el --- Collections, the program and the index  -*- lexical-binding: t; -*-

;;; Commentary:

;; The part of the orgsyndb package that the other parts build on: the
;; program the package runs, collections and the kinds of their files,
;; the collection index that `orgsyndb index' prints, the front matter
;; of Org sources, and the queue that runs, one at a time per
;; collection, the program's commands that write a collection's build
;; output.

;;; Code:

(require 'cl-lib)
(require 'subr-x)
(require 'osdb-org)

(defgroup orgsyndb nil
  "Edit the procedures, sequences and compounds of OrgSynDB collections."
  :group 'text
  :prefix "orgsyndb-")

(defconst orgsyndb--default-program
  (let* ((loaded (or load-file-name
                     (bound-and-true-p byte-compile-current-file)))
         (source (and loaded (expand-file-name "orgsyndb.el"
                                               (file-name-directory loaded))))
         (program (and source (file-exists-p source)
                       (expand-file-name
                        "../tools/orgsyndb"
                        (file-name-directory (file-truename source))))))
    (if (and program (file-exists-p program)) program "orgsyndb"))
  "The program of the checkout that holds this package, or `orgsyndb'.")

(defcustom orgsyndb-program orgsyndb--default-program
  "The OrgSynDB program that the package runs.
The default is `tools/orgsyndb' of the checkout whose `emacs/' holds
the package, or `orgsyndb' on `exec-path' when the package was not
loaded from a checkout."
  :type 'file
  :group 'orgsyndb)

(defconst orgsyndb--marker "orgsyndb.toml"
  "The file that marks the directory of a collection.")

(defconst orgsyndb--kinds
  '(("\\`org/procedures/[^/]+\\.org\\'" . org-procedure)
    ("\\`md/procedures/[^/]+\\.md\\'" . md-procedure)
    ("\\`md/sequences/[^/]+\\.md\\'" . sequence)
    ("\\`orgsyndb\\.toml\\'" . settings))
  "The kinds of collection files, each with the collection-relative path
that it matches.")

(defvar-local orgsyndb--root nil
  "The collection of the buffer's file, a directory name, or nil.")

(defvar-local orgsyndb--kind nil
  "The kind of the buffer's file, as `orgsyndb-file-kind' gives it.")

;;;; Collections and files

(defun orgsyndb--normal-root (directory)
  "Return DIRECTORY as the package keys a collection: absolute, as a
directory name."
  (file-name-as-directory (expand-file-name directory)))

(defun orgsyndb-collection-root (file)
  "Return the collection of FILE, or nil.
That is the nearest directory at or above the directory of FILE that
holds `orgsyndb.toml', as an absolute directory name.  FILE may be a
directory name, which then is the starting point."
  (when file
    (let ((root (locate-dominating-file
                 (file-name-directory (expand-file-name file))
                 orgsyndb--marker)))
      (and root (orgsyndb--normal-root root)))))

(defun orgsyndb-file-kind (file)
  "Return the kind of FILE in its collection, or nil.
The kind is `org-procedure' for a `.org' file directly in
`org/procedures/', `md-procedure' for a `.md' file directly in
`md/procedures/', `sequence' for a `.md' file directly in
`md/sequences/' and `settings' for `orgsyndb.toml'.  It is nil for any
other file and for a file outside every collection."
  (let ((root (orgsyndb-collection-root file)))
    (when root
      (let ((relative (file-relative-name (expand-file-name file) root))
            (case-fold-search nil))
        (cdr (cl-find-if (lambda (entry)
                           (string-match-p (car entry) relative))
                         orgsyndb--kinds))))))

(defun orgsyndb--current-root (&optional noerror)
  "Return the collection of the current buffer.
That is the collection of its file, or else of `default-directory'.
Signal a user error when there is none, unless NOERROR."
  (or orgsyndb--root
      (orgsyndb-collection-root (or buffer-file-name
                                    (expand-file-name default-directory)))
      (unless noerror
        (user-error "Not in an OrgSynDB collection: no %s above %s"
                    orgsyndb--marker default-directory))))

(defun orgsyndb--language-code (file)
  "Return the language code of the content FILE's name, or nil.
That is the two letters before `.md' or `.org', as in
`OSDB-0001-ethyl-acetate.de.md'."
  (let ((case-fold-search nil))
    (and file
         (string-match "\\.\\([a-z][a-z]\\)\\.\\(?:md\\|org\\)\\'" file)
         (match-string 1 file))))

(defun orgsyndb--file-id (file)
  "Return the procedure or sequence ID at the start of FILE's name, or nil."
  (let ((case-fold-search nil)
        (name (file-name-nondirectory file)))
    (and (string-match "\\`\\(\\(?:OSDB\\|SEQ\\)-[0-9]\\{4\\}\\)-" name)
         (match-string 1 name))))

(defun orgsyndb--now ()
  "Return the current time."
  (current-time))

(defun orgsyndb--offset-text (seconds)
  "Return the UTC offset SECONDS as `+HH:MM'."
  (format "%s%02d:%02d" (if (< seconds 0) "-" "+")
          (/ (abs seconds) 3600) (/ (% (abs seconds) 3600) 60)))

(defun orgsyndb--org-timestamp (time)
  "Return TIME as an Org timestamp `[YYYY-MM-DD Day hh:mm:ss]' of the
Europe/Berlin local time, with the English weekday."
  (let ((system-time-locale "C"))
    (format-time-string "[%Y-%m-%d %a %H:%M:%S]" time osdb-org-zone)))

(defun orgsyndb--rfc3339 (time)
  "Return TIME as `YYYY-MM-DDThh:mm:ss+HH:MM' in Europe/Berlin."
  (osdb-org-rfc3339 (time-convert time 'integer)))

;;;; Running the program

(defun orgsyndb--arguments (root args)
  "Return the program's arguments for the collection ROOT and ARGS."
  (append (list "-C" (directory-file-name (expand-file-name root))) args))

(defun orgsyndb--error-text (output)
  "Return the line of the program's error OUTPUT that says what failed.
That is its first `orgsyndb: error:' line, or else its last line that
is not blank, or else a note that it said nothing."
  (let ((lines (split-string output "\n" t "[ \t\r]+")))
    (or (cl-find-if (lambda (line) (string-prefix-p "orgsyndb: error:" line))
                    lines)
        (car (last lines))
        "the program wrote no error message")))

(defun orgsyndb--call (root &rest args)
  "Run the program for the collection ROOT with ARGS, and wait.
Return (STATUS STDOUT STDERR): the exit status, or a string when the
program could not be started, and the output decoded as UTF-8."
  (let ((default-directory root)
        (coding-system-for-read 'utf-8)
        (errors (make-temp-file "orgsyndb-stderr")))
    (unwind-protect
        (with-temp-buffer
          (let ((status (condition-case err
                            (apply #'call-process orgsyndb-program nil
                                   (list t errors) nil
                                   (orgsyndb--arguments root args))
                          (file-error (error-message-string err)))))
            (list status (buffer-string)
                  (with-temp-buffer
                    (insert-file-contents errors)
                    (buffer-string)))))
      (delete-file errors))))

(defun orgsyndb--drain (pipe)
  "Read what is left of the pipe process PIPE, then delete it."
  (when (process-live-p pipe)
    (while (accept-process-output pipe 0.05))
    (delete-process pipe)))

(cl-defun orgsyndb--start (root args &key buffer name filter on-exit)
  "Start the program for the collection ROOT with ARGS in the background.
With BUFFER, both output streams go into that buffer, through FILTER
when it is given; without it, standard output and standard error are
kept apart.  When the program ends, ON-EXIT, when given, is called with
the exit status, or `killed' when a signal ended it, and the text of
standard output and of standard error, the latter empty with BUFFER.
NAME names the process.  Return the process, which carries the
property `orgsyndb' with ROOT.  Signal an error when the program cannot
be started."
  (let* ((default-directory root)
         (stdout (or buffer (generate-new-buffer " *orgsyndb output*")))
         (stderr (unless buffer
                   (make-pipe-process
                    :name (concat (or name "orgsyndb") " stderr")
                    :buffer (generate-new-buffer " *orgsyndb stderr*")
                    :coding 'utf-8 :noquery t :sentinel #'ignore)))
         (process
          (make-process
           :name (or name "orgsyndb")
           :buffer stdout
           :stderr stderr
           :command (cons orgsyndb-program (orgsyndb--arguments root args))
           :coding 'utf-8
           :connection-type 'pipe
           :noquery t
           :filter filter
           :sentinel
           (lambda (process _event)
             (unless (process-live-p process)
               (let ((errors ""))
                 (when stderr
                   (orgsyndb--drain stderr)
                   (with-current-buffer (process-buffer stderr)
                     (setq errors (buffer-string)))
                   (kill-buffer (process-buffer stderr)))
                 (let ((output (if (buffer-live-p stdout)
                                   (with-current-buffer stdout
                                     (buffer-string))
                                 "")))
                   (unless buffer
                     (kill-buffer stdout))
                   (when on-exit
                     (funcall on-exit
                              (if (eq (process-status process) 'signal)
                                  'killed
                                (process-exit-status process))
                              output errors)))))))))
    (process-put process 'orgsyndb root)
    process))

(defun orgsyndb--command-buffer-name (what root)
  "Return the name of the buffer of the program's WHAT for the collection
ROOT, which the name gives as `abbreviate-file-name' does."
  (format "*orgsyndb %s %s*" what
          (abbreviate-file-name (directory-file-name root))))

(defun orgsyndb--command-buffer (what root)
  "Return the buffer of the program's WHAT for the collection ROOT,
emptied."
  (let ((buffer (get-buffer-create (orgsyndb--command-buffer-name what root))))
    (with-current-buffer buffer
      (let ((inhibit-read-only t))
        (erase-buffer)))
    buffer))

;;;; One command at a time

(cl-defstruct (orgsyndb--job (:constructor orgsyndb--make-job))
  "A command waiting for, or holding, a collection's turn."
  kind run then)

(defvar orgsyndb--queues (make-hash-table :test #'equal)
  "Map each collection to (RUNNING . WAITING): the job that holds the
collection's turn, or nil, and the jobs waiting for it, in order.")

(defun orgsyndb--enqueue (root kind run &optional then)
  "Run the command RUN for the collection ROOT when its turn comes.
RUN is called with a function FINISH, which it must call with a status
once its command no longer writes the collection's build output; the
next job then starts, and THEN, when given, is called with the same
status.  KIND names the command; a job of the kind `validate' or
`build' that is already waiting is not added again, and THEN joins
the waiting one's.  An error that RUN signals ends its turn."
  (let* ((root (orgsyndb--normal-root root))
         (queue (or (gethash root orgsyndb--queues)
                    (puthash root (list nil) orgsyndb--queues)))
         (waiting (and (memq kind '(validate build))
                       (cl-find kind (cdr queue) :key #'orgsyndb--job-kind))))
    (if waiting
        (when then
          (setf (orgsyndb--job-then waiting)
                (append (orgsyndb--job-then waiting) (list then))))
      (setcdr queue (append (cdr queue)
                            (list (orgsyndb--make-job
                                   :kind kind :run run
                                   :then (and then (list then))))))
      (orgsyndb--next root))))

(defun orgsyndb--next (root)
  "Start the next job of the collection ROOT when none holds its turn."
  (let ((queue (gethash root orgsyndb--queues)))
    (when (and queue (null (car queue)) (cdr queue))
      (let ((job (pop (cdr queue)))
            (done nil))
        (setcar queue job)
        (let ((finish
               (lambda (status)
                 (unless done
                   (setq done t)
                   (setcar queue nil)
                   (dolist (then (orgsyndb--job-then job))
                     (condition-case err
                         (funcall then status)
                       (error (message "orgsyndb: %s"
                                       (error-message-string err)))))
                   (orgsyndb--next root)))))
          (condition-case err
              (funcall (orgsyndb--job-run job) finish)
            (error
             (message "orgsyndb: %s" (error-message-string err))
             (funcall finish 'failed))))))))

;;;; The collection index

(defvar orgsyndb--indexes (make-hash-table :test #'equal)
  "Map each collection to its parsed index.")

(defvar orgsyndb--refreshing (make-hash-table :test #'equal)
  "Map each collection whose index is being refreshed in the background
to t, or to `again' when a save asked for one more refresh.")

(defun orgsyndb--parse-index (json)
  "Parse the index JSON: objects as alists keyed by symbols, arrays as
lists, null as nil and false as `:false'."
  (json-parse-string json :object-type 'alist :array-type 'list
                     :null-object nil :false-object :false))

(defun orgsyndb--fetch-index (root)
  "Run the program for the index of the collection ROOT and return it.
On success the package keeps it.  Signal an error with the program's
message when the run fails."
  (pcase-let ((`(,status ,output ,errors) (orgsyndb--call root "index")))
    (unless (eq status 0)
      (error "orgsyndb index: %s"
             (if (stringp status) status (orgsyndb--error-text errors))))
    (puthash root (orgsyndb--parse-index output) orgsyndb--indexes)))

(defun orgsyndb-index (&optional collection)
  "Return the index of COLLECTION, by default the current buffer's.
The first time a collection needs it, the program runs synchronously;
afterwards the package keeps it and refreshes it after each save of a
collection file.  Signal an error when the first run fails."
  (let ((root (if collection
                  (orgsyndb--normal-root collection)
                (orgsyndb--current-root))))
    (or (gethash root orgsyndb--indexes)
        (orgsyndb--fetch-index root))))

;;;###autoload
(defun orgsyndb-refresh-index ()
  "Read the index of the current collection again.
When the program fails, the earlier index stays and its error is shown."
  (interactive)
  (let ((root (orgsyndb--current-root)))
    (condition-case err
        (progn (orgsyndb--fetch-index root)
               (message "orgsyndb: index of %s read" root))
      (error (message "%s" (error-message-string err))))))

(defun orgsyndb--refresh-index-later (root)
  "Refresh the index of the collection ROOT in the background.
A failed run keeps the index and shows the program's error."
  (if (gethash root orgsyndb--refreshing)
      (puthash root 'again orgsyndb--refreshing)
    (puthash root t orgsyndb--refreshing)
    (let ((done (lambda ()
                  (let ((again (eq (gethash root orgsyndb--refreshing)
                                   'again)))
                    (remhash root orgsyndb--refreshing)
                    (when again
                      (orgsyndb--refresh-index-later root))))))
      (condition-case err
          (orgsyndb--start
           root '("index") :name "orgsyndb index"
           :on-exit
           (lambda (status output errors)
             (pcase status
               (0 (condition-case err
                      (puthash root (orgsyndb--parse-index output)
                               orgsyndb--indexes)
                    (error (message "orgsyndb index: %s"
                                    (error-message-string err)))))
               ('killed)
               (_ (message "orgsyndb index: %s"
                           (orgsyndb--error-text errors))))
             (funcall done)))
        (error
         (message "orgsyndb index: %s" (error-message-string err))
         (funcall done))))))

;;;; Org sources

(defvar orgsyndb--org-cache (make-hash-table :test #'equal)
  "Map each Org source file to (MODIFICATION-TIME . FRONT-MATTER).")

(defvar-local orgsyndb--org-buffer-cache nil
  "(TICK . FRONT-MATTER) of the buffer's text at its modification TICK.")

(defun orgsyndb--org-front-matter (file)
  "Return the front matter of the Org source FILE.
It is read from the text of the buffer visiting FILE, when there is
one, and otherwise from the file, again only when its modification
time changes."
  (let ((buffer (find-buffer-visiting file)))
    (if buffer
        (with-current-buffer buffer
          (let ((tick (buffer-chars-modified-tick)))
            (unless (eql (car orgsyndb--org-buffer-cache) tick)
              (setq orgsyndb--org-buffer-cache
                    (cons tick (osdb-org-front-matter
                                (buffer-substring-no-properties
                                 (point-min) (point-max))))))
            (cdr orgsyndb--org-buffer-cache)))
      (let ((modified (file-attribute-modification-time
                       (file-attributes file)))
            (cached (gethash file orgsyndb--org-cache)))
        (if (and cached (equal (car cached) modified))
            (cdr cached)
          (let ((front-matter
                 (and modified
                      (with-temp-buffer
                        (insert-file-contents file)
                        (osdb-org-front-matter (buffer-string))))))
            (puthash file (cons modified front-matter) orgsyndb--org-cache)
            front-matter))))))

(defun orgsyndb-procedures (&optional collection)
  "Return one record per entry of the index's `procedures' of COLLECTION.
A record is the entry, the `front_matter' of an Org source taken from
`osdb-org-front-matter'.  COLLECTION defaults to the current buffer's."
  (let ((root (if collection
                  (orgsyndb--normal-root collection)
                (orgsyndb--current-root))))
    (mapcar (lambda (entry)
              (if (equal (alist-get 'format entry) "org")
                  (cons (cons 'front_matter
                              (orgsyndb--org-front-matter
                               (expand-file-name (alist-get 'path entry)
                                                 root)))
                        (assq-delete-all 'front_matter (copy-alist entry)))
                entry))
            (alist-get 'procedures (orgsyndb-index root)))))

;;;; Reading the index

(defun orgsyndb--schema (root &rest keys)
  "Return the value of the index's `schema' of ROOT at KEYS."
  (let ((value (alist-get 'schema (orgsyndb-index root))))
    (dolist (key keys value)
      (setq value (alist-get key value)))))

(defun orgsyndb--declarations (root entity)
  "Return the fields of ENTITY in ROOT, a symbol: `compound' for the
registry fields, `procedure' for the declared procedure fields."
  (alist-get entity (alist-get 'fields (orgsyndb-index root))))

(defun orgsyndb--declaration (root entity key)
  "Return the declaration of the field KEY, a string, of ENTITY in ROOT."
  (cl-find key (orgsyndb--declarations root entity)
           :key (lambda (field) (alist-get 'key field)) :test #'equal))

(defun orgsyndb--vocabulary (root name)
  "Return the values of the vocabulary NAME, a string, in ROOT, an alist
of value symbols to their labels and parents."
  (alist-get (intern name) (alist-get 'vocabularies (orgsyndb-index root))))

(defun orgsyndb--compounds (root)
  "Return the compound entries of the index of ROOT, one per substance of
its registry, each an alist of `key', `data' and `url'."
  (alist-get 'compounds (orgsyndb-index root)))

(defun orgsyndb--accounts (root)
  "Return the account entries of the index of ROOT, one per account of
its registry, each an alist of `username' and `name'."
  (alist-get 'accounts (orgsyndb-index root)))

(defun orgsyndb--compound (root key)
  "Return the data of the compound KEY in ROOT, or nil."
  (alist-get 'data (cl-find key (orgsyndb--compounds root)
                            :key (lambda (entry) (alist-get 'key entry))
                            :test #'equal)))

(defun orgsyndb--structure-images (root)
  "Return `structures/<name>' for each SVG or PNG image directly in the
`static/structures/' of ROOT."
  (let ((directory (expand-file-name "static/structures/" root)))
    (and (file-directory-p directory)
         (mapcar (lambda (name) (concat "structures/" name))
                 (directory-files directory nil "\\.\\(?:svg\\|png\\)\\'")))))

(defun orgsyndb--entries-of (root id)
  "Return the records of the procedure or sequence ID in ROOT, in file
name order."
  (sort (cl-remove-if-not (lambda (entry)
                            (equal (alist-get 'id entry) id))
                          (if (string-prefix-p "SEQ-" id)
                              (alist-get 'sequences (orgsyndb-index root))
                            (orgsyndb-procedures root)))
        (lambda (a b)
          (string< (file-name-nondirectory (alist-get 'path a))
                   (file-name-nondirectory (alist-get 'path b))))))

(defun orgsyndb--definition (root id language)
  "Return the record of ID in ROOT that a file in LANGUAGE refers to.
That is the file whose language code is LANGUAGE, else the file
without a code, else the first file in name order."
  (let ((entries (orgsyndb--entries-of root id)))
    (or (and language
             (cl-find language entries
                      :key (lambda (entry) (alist-get 'language entry))
                      :test #'equal))
        (cl-find nil entries :key (lambda (entry) (alist-get 'language entry)))
        (car entries))))

(provide 'orgsyndb-core)

;;; orgsyndb-core.el ends here

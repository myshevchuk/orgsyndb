;;; orgsyndb-preview.el --- Preview and PDF  -*- lexical-binding: t; -*-

;;; Commentary:

;; One `orgsyndb serve' per collection, a build for each later preview,
;; the page of the file being edited in the browser, an optional build
;; after each save, and the PDF of a procedure.

;;; Code:

(require 'orgsyndb-core)
(require 'browse-url)

(defcustom orgsyndb-preview-port 8000
  "The port on which `orgsyndb-serve' serves a collection's site."
  :type 'natnum
  :group 'orgsyndb)

(defcustom orgsyndb-preview-delay 1.0
  "Seconds without another save after which
`orgsyndb-preview-on-save-mode' builds the site."
  :type 'number
  :group 'orgsyndb)

(defvar orgsyndb--servers (make-hash-table :test #'equal)
  "Map each collection to its serve process, or to `starting' while the
process waits for its turn.")

(defun orgsyndb-page-url (file)
  "Return the URL of the site page of the collection FILE.
That is `http://127.0.0.1:<port>/' followed by `procedures/<id>/' for
a procedure and `sequences/<id>/' for a sequence, the ID in lower case,
and by nothing for any other file; the port is `orgsyndb-preview-port'."
  (concat (format "http://127.0.0.1:%d/" orgsyndb-preview-port)
          (pcase (orgsyndb-file-kind file)
            ((or 'org-procedure 'md-procedure)
             (format "procedures/%s/" (downcase (orgsyndb--file-id file))))
            ('sequence
             (format "sequences/%s/" (downcase (orgsyndb--file-id file))))
            (_ ""))))

(defun orgsyndb--server (root)
  "Return the serve process of the collection ROOT, `starting' while it
waits for its turn, or nil."
  (let ((server (gethash root orgsyndb--servers)))
    (cond ((eq server 'starting) server)
          ((and server (process-live-p server)) server))))

(defun orgsyndb--serve (root &optional then)
  "Start the serve process of the collection ROOT when its turn comes.
THEN, when given, is called with `serving' once the process prints its
`serving' line, or with its exit status when it ends before."
  (puthash root 'starting orgsyndb--servers)
  (orgsyndb--enqueue
   root 'serve
   (lambda (finish)
     (let ((buffer (orgsyndb--command-buffer "serve" root))
           (serving nil)
           (said ""))
       (condition-case err
           (puthash
            root
            (orgsyndb--start
             root (list "serve" "--port"
                        (number-to-string orgsyndb-preview-port))
             :buffer buffer :name "orgsyndb serve"
             :filter
             (lambda (process output)
               (when (buffer-live-p (process-buffer process))
                 (with-current-buffer (process-buffer process)
                   (save-excursion
                     (goto-char (point-max))
                     (insert output))))
               (unless serving
                 (setq said (concat said output))
                 (when (string-match-p "^serving " said)
                   (setq serving t
                         said nil)
                   (funcall finish 'serving))))
             :on-exit
             (lambda (status _output _errors)
               (remhash root orgsyndb--servers)
               (unless serving
                 (setq serving t)
                 (display-buffer buffer)
                 (funcall finish status))))
            orgsyndb--servers)
         (error (remhash root orgsyndb--servers)
                (signal (car err) (cdr err))))))
   then))

;;;###autoload
(defun orgsyndb-serve ()
  "Serve the current collection's site, building it first."
  (interactive)
  (let ((root (orgsyndb--current-root)))
    (if (orgsyndb--server root)
        (message "orgsyndb: the site of %s is served already" root)
      (orgsyndb--serve root
                       (lambda (status)
                         (when (eq status 'serving)
                           (message "orgsyndb: serving http://127.0.0.1:%d/"
                                    orgsyndb-preview-port)))))))

;;;###autoload
(defun orgsyndb-stop-server ()
  "Stop serving the current collection's site."
  (interactive)
  (let* ((root (orgsyndb--current-root))
         (server (orgsyndb--server root)))
    (if (processp server)
        (progn (delete-process server)
               (remhash root orgsyndb--servers))
      (message "orgsyndb: no server runs for %s" root))))

(defun orgsyndb--build (root then)
  "Build the site of the collection ROOT when its turn comes, and call
THEN with the exit status."
  (orgsyndb--enqueue
   root 'build
   (lambda (finish)
     (orgsyndb--start root '("build") :name "orgsyndb build"
                      :buffer (orgsyndb--command-buffer "build" root)
                      :on-exit (lambda (status &rest _)
                                 (funcall finish status))))
   then))

(defun orgsyndb--build-failed (root)
  "Show the output of the failed build of ROOT."
  (display-buffer (orgsyndb--command-buffer-name "build" root)))

(defun orgsyndb--published (root file)
  "Return the file that the site publishes for the procedure or sequence
FILE of ROOT: the variant in the site's language, else the one
without a language code, else the first."
  (let* ((id (orgsyndb--file-id file))
         (entries (and id (orgsyndb--entries-of root id)))
         (language (alist-get 'site_language (orgsyndb-index root)))
         (entry (or (cl-find language entries
                             :key (lambda (entry) (alist-get 'language entry))
                             :test #'equal)
                    (cl-find nil entries
                             :key (lambda (entry) (alist-get 'language entry)))
                    (car entries))))
    (and entry (expand-file-name (alist-get 'path entry) root))))

;;;###autoload
(defun orgsyndb-preview ()
  "Show the site page of the current file in the browser.
The first preview of a collection starts its server; a later one
builds the site again first."
  (interactive)
  (let* ((root (orgsyndb--current-root))
         (file (or buffer-file-name root))
         (url (orgsyndb-page-url file))
         (published (and (memq (orgsyndb-file-kind file)
                               '(org-procedure md-procedure sequence))
                         (orgsyndb--published root file))))
    (when (and published (not (equal published file)))
      (message "orgsyndb: the page shows %s, the variant the site publishes"
               (file-name-nondirectory published)))
    (pcase (orgsyndb--server root)
      ('starting (message "orgsyndb: the server of %s is starting" root))
      ('nil (orgsyndb--serve root (lambda (status)
                                    (when (eq status 'serving)
                                      (browse-url url)))))
      (_ (orgsyndb--build root (lambda (status)
                                 (if (eq status 0)
                                     (browse-url url)
                                   (orgsyndb--build-failed root))))))))

;;;; Building after each save

(defvar-local orgsyndb--preview-timer nil
  "The timer of the build that the last save asked for.")

(defun orgsyndb--preview-after-save ()
  "Build the site once `orgsyndb-preview-delay' passes without a save."
  (when (timerp orgsyndb--preview-timer)
    (cancel-timer orgsyndb--preview-timer))
  (let ((root (orgsyndb--current-root)))
    (setq orgsyndb--preview-timer
          (run-with-timer orgsyndb-preview-delay nil
                          (lambda ()
                            (when (processp (orgsyndb--server root))
                              (orgsyndb--build
                               root (lambda (status)
                                      (unless (eq status 0)
                                        (orgsyndb--build-failed root))))))))))

;;;###autoload
(define-minor-mode orgsyndb-preview-on-save-mode
  "Build the collection's site after each save, while it is served.
The build starts once `orgsyndb-preview-delay' seconds pass without
another save; reload the page in the browser to see it."
  :lighter nil
  (if orgsyndb-preview-on-save-mode
      (add-hook 'after-save-hook #'orgsyndb--preview-after-save nil t)
    (remove-hook 'after-save-hook #'orgsyndb--preview-after-save t)
    (when (timerp orgsyndb--preview-timer)
      (cancel-timer orgsyndb--preview-timer))))

;;;; PDF

;;;###autoload
(defun orgsyndb-pdf ()
  "Build the PDFs of the current collection and show the current
procedure's."
  (interactive)
  (let* ((root (orgsyndb--current-root))
         (file buffer-file-name)
         (id (and file
                  (memq (orgsyndb-file-kind file)
                        '(org-procedure md-procedure))
                  (orgsyndb--file-id file)))
         (name (orgsyndb--command-buffer-name "pdf" root)))
    (orgsyndb--enqueue
     root 'pdf
     (lambda (finish)
       (orgsyndb--start root '("pdf") :name "orgsyndb pdf"
                        :buffer (orgsyndb--command-buffer "pdf" root)
                        :on-exit (lambda (status &rest _)
                                   (funcall finish status))))
     (lambda (status)
       (cond
        ((not (eq status 0)) (display-buffer name))
        (id
         (let* ((directory (expand-file-name "pdf/" root))
                (pdf (and (file-directory-p directory)
                          (car (directory-files
                                directory t
                                (concat "\\`" (regexp-quote id) "-"))))))
           (if pdf
               (find-file-other-window pdf)
             (message "orgsyndb: pdf/ holds no PDF of %s" id)))))))))

(provide 'orgsyndb-preview)

;;; orgsyndb-preview.el ends here

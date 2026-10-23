;;; export.el --- Export OrgSynDB Org procedures with ox-hugo  -*- lexical-binding: t; -*-

;;; Commentary:

;; Usage: emacs -Q --batch -l tools/export.el PLAN_JSON STAGING_DIR
;;
;; Exports every entry of PLAN_JSON (written by `pipeline.write_export_plan')
;; to STAGING_DIR/<stem>.md.  ox-hugo and tomelr are installed into
;; <app>/.emacs-batch/elpa/ at pinned commits on first use, and every run
;; checks the installed checkouts against the pins.  Temporary files go
;; to tmp/ beside STAGING_DIR, the collection's build/tmp/.  Nothing is
;; read from or written to the user's own Emacs directories or the
;; inherited TMPDIR.  Exits 0 on success; on any error it prints
;; "export.el: <source>: <message>" (or "export.el: error: <message>"
;; when no source is involved) and exits 1.

;;; Code:

;; Isolation.  These must be set before package.el or Org is loaded:
;; package.el derives its GnuPG directory from `package-user-dir' when it
;; loads, and org-persist creates its directory in
;; `temporary-file-directory' when Org loads.

(defconst osdb-app
  (file-name-directory
   (directory-file-name
    (file-name-directory (expand-file-name load-file-name))))
  "The application root, as a directory name.")

(defconst osdb-batch-dir (expand-file-name ".emacs-batch/" osdb-app)
  "The Emacs directory of the export, inside the application.")

(unless (= (length command-line-args-left) 2)
  (message "export.el: error: usage: emacs -Q --batch -l tools/export.el \
PLAN_JSON STAGING_DIR")
  (kill-emacs 1))

(defconst osdb-tmp-dir
  (expand-file-name "tmp/" (file-name-directory
                            (directory-file-name
                             (expand-file-name
                              (cadr command-line-args-left)))))
  "The temporary directory of the export: tmp/ beside STAGING_DIR.")

(make-directory osdb-tmp-dir t)
(setq user-emacs-directory osdb-batch-dir
      package-user-dir (expand-file-name "elpa" osdb-batch-dir)
      package-gnupghome-dir (expand-file-name "elpa/gnupg" osdb-batch-dir)
      temporary-file-directory osdb-tmp-dir)
(setenv "TMPDIR" (directory-file-name osdb-tmp-dir))

;; Git variables inherited from a hook would point the pin check and the
;; bootstrap at the outer repository instead of the package checkouts.
(dolist (name '("GIT_DIR" "GIT_WORK_TREE" "GIT_INDEX_FILE"
                "GIT_OBJECT_DIRECTORY" "GIT_ALTERNATE_OBJECT_DIRECTORIES"
                "GIT_PREFIX" "GIT_COMMON_DIR"))
  (setenv name nil))

;; Precaution: keep any native compilation inside the repository.
(when (featurep 'native-compile)
  (setq native-comp-jit-compilation nil)
  (when (fboundp 'startup-redirect-eln-cache)
    (startup-redirect-eln-cache
     (expand-file-name "eln-cache/" osdb-batch-dir))))

(setq enable-local-variables nil)
(prefer-coding-system 'utf-8-unix)

(defconst osdb-pins
  '((tomelr "https://github.com/kaushalmodi/tomelr"
            "670e0a08f625175fd80137cf69e799619bf8a381")
    (ox-hugo "https://github.com/kaushalmodi/ox-hugo"
             "b7dc44dc28911b9d8e3055a18deac16c3b560b03"))
  "Package, upstream URL and pinned commit, in installation order.")

(defun osdb-fail (where message)
  "Print MESSAGE about WHERE (a source, or nil) to stderr and exit 1."
  (message "export.el: %s: %s" (or where "error") message)
  (kill-emacs 1))

(defun osdb-checkout-head (dir)
  "Return the commit checked out in DIR, or signal an error."
  (with-temp-buffer
    (let ((status (call-process "git" nil t nil "-C" dir
                                "rev-parse" "HEAD")))
      (unless (eq status 0)
        (error "Cannot read the commit of %s: %s" dir
               (string-trim (buffer-string))))
      (string-trim (buffer-string)))))

(defun osdb-bootstrap ()
  "Install any missing pinned package, then check every pin.
Signals an error naming the package, both commits and the remedy when
a checkout is not at its pin."
  (require 'package)
  (require 'package-vc)
  (setq package-archives nil
        package-vc-register-as-project nil)
  (package-initialize)
  (dolist (pin osdb-pins)
    (pcase-let ((`(,name ,url ,commit) pin))
      (unless (package-installed-p name)
        (message "export.el: installing %s at %s" name commit)
        (package-vc-install (list name :url url) commit))))
  (dolist (pin osdb-pins)
    (pcase-let* ((`(,name ,_url ,commit) pin)
                 (desc (cadr (assq name package-alist)))
                 (dir (if desc (package-desc-dir desc)
                        (expand-file-name (symbol-name name)
                                          package-user-dir)))
                 (head (osdb-checkout-head dir)))
      (unless (equal head commit)
        (error "%s is checked out at %s, but its pin is %s; run \
tools/orgsyndb clean --all, then export again" name head commit)))))

(defun osdb-table-entry-p (entry)
  "Return non-nil when front-matter ENTRY has a TOML table as its value."
  (and (consp entry) (cdr entry) (tomelr-toml-table-p (cdr entry))))

(defun osdb-tables-last (args)
  "Move the table-valued entries of the front matter in ARGS last.
ARGS are the arguments of `org-hugo--gen-front-matter'.  The relative
order within each group is kept, so tomelr writes every table header
after all plain keys."
  (let ((data (car args)))
    (cons (append (seq-remove #'osdb-table-entry-p data)
                  (seq-filter #'osdb-table-entry-p data))
          (cdr args))))

(defun osdb-setup ()
  "Load ox-hugo, check the functions the guard needs, and set options."
  (require 'ox-hugo)
  (dolist (fn '(org-hugo--gen-front-matter tomelr-toml-table-p))
    (unless (fboundp fn)
      (error "%s is not defined by the pinned ox-hugo and tomelr" fn)))
  (advice-add 'org-hugo--gen-front-matter :filter-args #'osdb-tables-last)
  (setq org-export-with-author nil
        org-html-with-latex 'verbatim
        org-export-with-sub-superscripts '{}
        org-export-use-babel nil
        org-hugo-auto-set-lastmod nil
        org-export-coding-system 'utf-8-unix))

(defun osdb-read-plan (file)
  "Return the entries of the JSON export plan FILE as alists."
  (with-temp-buffer
    (let ((coding-system-for-read 'utf-8))
      (insert-file-contents file))
    (json-parse-buffer :object-type 'alist :array-type 'list
                       :null-object nil :false-object nil)))

(defun osdb-export-entry (entry staging)
  "Export plan ENTRY to STAGING/<stem>.md and return the file name."
  (let-alist entry
    (let ((org-hugo-base-dir (file-name-directory
                              (directory-file-name staging)))
          (org-hugo-content-folder (file-name-nondirectory
                                    (directory-file-name staging)))
          (org-hugo-section "."))
      (with-temp-buffer
        (setq default-directory (file-name-directory .source))
        (let ((coding-system-for-read 'utf-8))
          (insert-file-contents .source))
        (org-mode)
        (goto-char (point-min))
        ;; Org replaces the extension of the export file name, so a
        ;; bare stem such as OSDB-0001-x.de would lose its language code.
        (insert "#+DATE: " .date "\n"
                "#+HUGO_LASTMOD: " .lastmod "\n"
                "#+EXPORT_FILE_NAME: " .stem ".md\n")
        (when .ai_model
          (insert "#+HUGO_CUSTOM_FRONT_MATTER: :ai_model "
                  (prin1-to-string .ai_model) "\n"))
        ;; Org draws reference IDs from `random'; seeding it with the
        ;; stem makes the anchors a function of this file alone.
        (random .stem)
        (org-hugo-export-to-md)))))

(defun osdb-main (args)
  "Export the plan named by ARGS, (PLAN_JSON STAGING_DIR), and exit.
The argument count is checked when this file loads."
  (let ((plan-file (expand-file-name (car args)))
        (staging (file-name-as-directory (expand-file-name (cadr args))))
        (count 0))
    (condition-case err
        (progn
          (unless (file-directory-p staging)
            (error "Staging directory %s does not exist" staging))
          (osdb-bootstrap)
          (osdb-setup))
      (error (osdb-fail nil (error-message-string err))))
    (dolist (entry (condition-case err
                       (osdb-read-plan plan-file)
                     (error (osdb-fail plan-file
                                       (error-message-string err)))))
      (let ((source (alist-get 'source entry)))
        (condition-case err
            (let ((written (osdb-export-entry entry staging))
                  (expected (expand-file-name
                             (concat (alist-get 'stem entry) ".md")
                             staging)))
              (unless (file-equal-p written expected)
                (error "Exported to %s instead of %s" written expected))
              (setq count (1+ count)))
          (error (osdb-fail source (error-message-string err))))))
    (message "export.el: exported %d files" count)
    (kill-emacs 0)))

(osdb-main (prog1 command-line-args-left
             (setq command-line-args-left nil)))

;;; export.el ends here

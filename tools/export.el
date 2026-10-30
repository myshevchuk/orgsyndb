;;; export.el --- Export OrgSynDB Org procedures with ox-hugo  -*- lexical-binding: t; -*-

;;; Commentary:

;; Usage: emacs -Q --batch -l tools/export.el ORG_ROOT STAGING_DIR
;;
;; Examines the Org sources in the directory ORG_ROOT with osdb-org.el,
;; beside this file, and prints each problem to stdout as
;; "<path>:<field>: <severity>: <message>"; nothing else goes to stdout.
;; When any problem is an error, it exits 1 without installing, loading
;; or exporting anything.  Otherwise it exports every source to
;; STAGING_DIR/<stem>.md with the date, lastmod and ai_model that
;; osdb-org.el chose.  ox-hugo and tomelr are cloned with git into
;; <app>/.emacs-batch/elpa/ at pinned commits on first use, and every run
;; that exports checks the installed checkouts against the pins.  Needs
;; Emacs 29.1 or later; package.el is not used.  Temporary files go to
;; tmp/ beside STAGING_DIR, the collection's build/tmp/.  Nothing is read
;; from or written to the user's own Emacs directories or the inherited
;; TMPDIR.  Exits 0 on success; on any other error it prints
;; "export.el: <source>: <message>" (or "export.el: error: <message>"
;; when no source is involved) to stderr and exits 1.

;;; Code:

;; Isolation.  These must be set before Org or osdb-org.el is loaded:
;; org-persist creates its directory in `temporary-file-directory' when
;; Org loads.

(defconst osdb-app
  (file-name-directory
   (directory-file-name
    (file-name-directory (expand-file-name load-file-name))))
  "The application root, as a directory name.")

(defconst osdb-batch-dir (expand-file-name ".emacs-batch/" osdb-app)
  "The Emacs directory of the export, inside the application.")

(when (version< emacs-version "29.1")
  (message "export.el: error: Emacs 29.1 or later is required; this is \
Emacs %s" emacs-version)
  (kill-emacs 1))

(unless (= (length command-line-args-left) 2)
  (message "export.el: error: usage: emacs -Q --batch -l tools/export.el \
ORG_ROOT STAGING_DIR")
  (kill-emacs 1))

(defconst osdb-tmp-dir
  (expand-file-name "tmp/" (file-name-directory
                            (directory-file-name
                             (expand-file-name
                              (cadr command-line-args-left)))))
  "The temporary directory of the export: tmp/ beside STAGING_DIR.")

(make-directory osdb-tmp-dir t)
(setq user-emacs-directory osdb-batch-dir
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

;; By file name, so that `load-path' stays as it is.
(require 'osdb-org (expand-file-name
                    "osdb-org"
                    (file-name-directory
                     (or load-file-name
                         (bound-and-true-p byte-compile-current-file)))))

;; Org, ox-hugo and tomelr load in `osdb-setup', after the Org sources
;; have been examined; their options are bound dynamically.
(defvar org-export-coding-system)
(defvar org-export-use-babel)
(defvar org-export-with-author)
(defvar org-export-with-sub-superscripts)
(defvar org-html-with-latex)
(defvar org-hugo-auto-set-lastmod)
(defvar org-hugo-base-dir)
(defvar org-hugo-content-folder)
(defvar org-hugo-section)
(declare-function org-hugo-export-to-md "ox-hugo")
(declare-function tomelr-toml-table-p "tomelr")
(declare-function tomelr-toml-table-array-p "tomelr")

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

(defun osdb-git (&rest args)
  "Run git with ARGS; return its trimmed output, or signal an error."
  (with-temp-buffer
    (unless (eq (apply #'call-process "git" nil t nil args) 0)
      (error "git %s failed: %s" (string-join args " ")
             (string-trim (buffer-string))))
    (string-trim (buffer-string))))

(defun osdb-bootstrap ()
  "Clone any missing pinned package, check every pin, extend `load-path'.
Signals an error naming the package when it cannot be installed, and
naming the package, both commits and the remedy when a checkout is not
at its pin."
  (dolist (pin osdb-pins)
    (pcase-let* ((`(,name ,url ,commit) pin)
                 (dir (expand-file-name (format "elpa/%s" name)
                                        osdb-batch-dir)))
      (unless (file-directory-p dir)
        (message "export.el: installing %s at %s" name commit)
        (condition-case err
            (progn
              (osdb-git "clone" "--quiet" url dir)
              (osdb-git "-C" dir "-c" "advice.detachedHead=false"
                        "checkout" "--quiet" commit))
          (error
           (delete-directory dir t)
           (error "Cannot install %s: %s" name
                  (error-message-string err)))))
      (let ((head (condition-case err
                      (osdb-git "-C" dir "rev-parse" "HEAD")
                    (error (error "Cannot read the commit of %s: %s" dir
                                  (error-message-string err))))))
        (unless (equal head commit)
          (error "%s is checked out at %s, but its pin is %s; run \
tools/orgsyndb clean --all, then export again" name head commit)))
      (add-to-list 'load-path dir))))

(defun osdb-table-entry-p (entry)
  "Return non-nil when front-matter ENTRY has a table as its value.
That is a TOML table or an array of TOML tables, which tomelr writes
under a [KEY] or [[KEY]] header."
  (and (consp entry) (cdr entry)
       (or (tomelr-toml-table-p (cdr entry))
           (tomelr-toml-table-array-p (cdr entry)))))

(defun osdb-tables-last (args)
  "Move the table-valued entries of the front matter in ARGS last.
ARGS are the arguments of `org-hugo--gen-front-matter'.  An entry is
table-valued when `osdb-table-entry-p' says so.  The relative order
within each group is kept, so tomelr writes every table header after
all plain keys."
  (let ((data (car args)))
    (cons (append (seq-remove #'osdb-table-entry-p data)
                  (seq-filter #'osdb-table-entry-p data))
          (cdr args))))

(defun osdb-setup ()
  "Load ox-hugo, check the functions the guard needs, and set options."
  (require 'ox-hugo)
  (dolist (fn '(org-hugo--gen-front-matter tomelr-toml-table-p
                tomelr-toml-table-array-p))
    (unless (fboundp fn)
      (error "%s is not defined by the pinned ox-hugo and tomelr" fn)))
  (advice-add 'org-hugo--gen-front-matter :filter-args #'osdb-tables-last)
  (setq org-export-with-author nil
        org-html-with-latex 'verbatim
        org-export-with-sub-superscripts '{}
        org-export-use-babel nil
        org-hugo-auto-set-lastmod nil
        org-export-coding-system 'utf-8-unix))

(defun osdb-export-source (source staging)
  "Export SOURCE to STAGING/<stem>.md and return the file name.
SOURCE is a plist of `osdb-org-examine'."
  (let ((file (plist-get source :path))
        (stem (plist-get source :stem))
        (ai-model (plist-get source :ai-model))
        (org-hugo-base-dir (file-name-directory
                            (directory-file-name staging)))
        (org-hugo-content-folder (file-name-nondirectory
                                  (directory-file-name staging)))
        (org-hugo-section "."))
    (with-temp-buffer
      (setq default-directory (file-name-directory file))
      (let ((coding-system-for-read 'utf-8-auto))
        (insert-file-contents file))
      (org-mode)
      (goto-char (point-min))
      ;; Org replaces the extension of the export file name, so a
      ;; bare stem such as OSDB-0001-x.de would lose its language code.
      (insert "#+DATE: " (plist-get source :date) "\n"
              "#+HUGO_LASTMOD: " (plist-get source :lastmod) "\n"
              "#+EXPORT_FILE_NAME: " stem ".md\n")
      (when ai-model
        (insert "#+HUGO_CUSTOM_FRONT_MATTER: :ai_model "
                (prin1-to-string ai-model) "\n"))
      ;; ox-hugo takes the date from the CLOSED line of the heading at
      ;; point; at the buffer start there is none.
      (goto-char (point-min))
      ;; Org draws reference IDs from `random'; seeding it with the
      ;; stem makes the anchors a function of this file alone.
      (random stem)
      (org-hugo-export-to-md))))

(defun osdb-report (problems)
  "Print PROBLEMS, (PATH . PROBLEM) pairs, to stdout, one line each.
Return non-nil when any of them is an error."
  (let ((errors nil))
    (pcase-dolist (`(,path . ,problem) problems)
      (princ (concat (osdb-org-problem-line path problem) "\n"))
      (when (equal (nth 1 problem) "error")
        (setq errors t)))
    errors))

(defun osdb-main (args)
  "Examine and export the sources named by ARGS, (ORG_ROOT STAGING_DIR).
Exit 1 when the zone is unknown, an argument is not a directory, the
sources have an error, or a step of the export fails, and 0 otherwise.
The argument count is checked when this file loads."
  (let ((org-root (car args))
        (staging (file-name-as-directory (expand-file-name (cadr args))))
        (count 0))
    (unless (osdb-org-zone-available-p)
      (osdb-fail nil (format "time zone %s is not available; install the \
tz database (tzdata)" osdb-org-zone)))
    (unless (file-directory-p org-root)
      (osdb-fail nil (format "%s is not a directory" org-root)))
    (unless (file-directory-p staging)
      (osdb-fail nil (format "Staging directory %s does not exist" staging)))
    (pcase-let ((`(,sources . ,problems) (osdb-org-examine org-root)))
      (when (osdb-report problems)
        (kill-emacs 1))
      (unless sources
        (message "export.el: no Org sources to export")
        (kill-emacs 0))
      (condition-case err
          (progn
            (osdb-bootstrap)
            (osdb-setup))
        (error (osdb-fail nil (error-message-string err))))
      (dolist (source sources)
        (condition-case err
            (let ((written (osdb-export-source source staging))
                  (expected (expand-file-name
                             (concat (plist-get source :stem) ".md")
                             staging)))
              (unless (file-equal-p written expected)
                (error "Exported to %s instead of %s" written expected))
              (setq count (1+ count)))
          (error (osdb-fail (plist-get source :path)
                            (error-message-string err))))))
    (message "export.el: exported %d files" count)
    (kill-emacs 0)))

(osdb-main (prog1 command-line-args-left
             (setq command-line-args-left nil)))

;;; export.el ends here

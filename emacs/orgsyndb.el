;;; orgsyndb.el --- Edit OrgSynDB collections  -*- lexical-binding: t; -*-

;; Author: Mykhailo Shevchuk
;; Version: 0.1.0
;; Package-Requires: ((emacs "29.1"))
;; Keywords: tools, outlines
;; URL: https://github.com/myshevchuk/orgsyndb

;;; Commentary:

;; A minor mode for the files of an OrgSynDB collection: Org and
;; Markdown procedures, synthesis sequences, compound files,
;; vocabularies and `orgsyndb.toml'.  `global-orgsyndb-mode' turns it on
;; in every buffer that visits such a file.  It completes front-matter
;; keys and values, finds the definitions and references of compound
;; keys and procedure IDs, describes them with eldoc, shows the problems
;; of the Org checks and of `orgsyndb validate' through Flymake or
;; Flycheck, keeps modification times current, and previews pages.
;; `C-c C-;' opens a menu of its commands.
;;
;; The package ships in the application's `emacs/' directory and runs
;; the program of the same checkout, `tools/orgsyndb'.

;;; Code:

(require 'orgsyndb-core)
(require 'orgsyndb-complete)
(require 'orgsyndb-xref)
(require 'orgsyndb-files)
(require 'orgsyndb-check)
(require 'orgsyndb-stamp)
(require 'orgsyndb-preview)
(require 'orgsyndb-structure)
(require 'transient)

(defcustom orgsyndb-diagnostics 'flymake
  "How the buffers of procedures, sequences and compounds show problems.
`flymake' turns on `flymake-mode' with the backend `orgsyndb-flymake',
`flycheck' turns on `flycheck-mode' with the checker `orgsyndb', and
nil shows them through neither."
  :type '(choice (const :tag "Flymake" flymake)
                 (const :tag "Flycheck" flycheck)
                 (const :tag "Neither" nil))
  :group 'orgsyndb)

(declare-function flycheck-mode "ext:flycheck" (&optional arg))
(defvar flycheck-checker)

(defconst orgsyndb--checked-kinds
  '(org-procedure md-procedure sequence compound)
  "The kinds of files whose problems the mode shows.")

(defvar-local orgsyndb--diagnostics nil
  "The diagnostics front end the mode turned on in the buffer, or nil.")

(defun orgsyndb--setup-diagnostics ()
  "Turn on the front end that `orgsyndb-diagnostics' names."
  (when (memq orgsyndb--kind orgsyndb--checked-kinds)
    (pcase orgsyndb-diagnostics
      ('flymake
       (add-hook 'flymake-diagnostic-functions #'orgsyndb-flymake nil t)
       (flymake-mode 1)
       (setq orgsyndb--diagnostics 'flymake))
      ('flycheck
       (require 'orgsyndb-flycheck)
       (if (require 'flycheck nil t)
           (progn (setq-local flycheck-checker 'orgsyndb)
                  (flycheck-mode 1)
                  (setq orgsyndb--diagnostics 'flycheck))
         (message "orgsyndb: Flycheck is not installed"))))))

(defun orgsyndb--teardown-diagnostics ()
  "Undo `orgsyndb--setup-diagnostics'."
  (remove-hook 'flymake-diagnostic-functions #'orgsyndb-flymake t)
  (pcase orgsyndb--diagnostics
    ('flymake (flymake-mode -1))
    ('flycheck (kill-local-variable 'flycheck-checker)
               (flycheck-mode -1)))
  (setq orgsyndb--diagnostics nil))

(defun orgsyndb--after-save ()
  "Refresh the index and validate the collection after a save."
  (when orgsyndb--root
    (orgsyndb--refresh-index-later orgsyndb--root)
    (when orgsyndb-validate-on-save
      (orgsyndb--validate-later orgsyndb--root))))

(defvar-keymap orgsyndb-mode-map
  :doc "The keymap of `orgsyndb-mode'."
  "C-c C-;" #'orgsyndb-dispatch)

;;;###autoload
(define-minor-mode orgsyndb-mode
  "Edit a file of an OrgSynDB collection.
Completion at point offers front-matter keys and values; `M-.' and
`M-?' find the definitions and references of compound keys and
procedure IDs; eldoc describes them; problems are shown as
`orgsyndb-diagnostics' says; saving updates the modification time and
validates the collection.  \\[orgsyndb-dispatch] opens a menu of the
commands.

\\{orgsyndb-mode-map}"
  :lighter " OSDB"
  :keymap orgsyndb-mode-map
  (if orgsyndb-mode
      (progn
        (setq orgsyndb--root (and buffer-file-name
                                  (orgsyndb-collection-root buffer-file-name))
              orgsyndb--kind (and buffer-file-name
                                  (orgsyndb-file-kind buffer-file-name)))
        (add-hook 'completion-at-point-functions
                  #'orgsyndb-completion-at-point nil t)
        (add-hook 'xref-backend-functions #'orgsyndb--xref-backend nil t)
        (add-hook 'eldoc-documentation-functions #'orgsyndb-eldoc nil t)
        (add-hook 'after-save-hook #'orgsyndb--after-save nil t)
        (orgsyndb--setup-timestamps)
        (orgsyndb--setup-diagnostics))
    (remove-hook 'completion-at-point-functions
                 #'orgsyndb-completion-at-point t)
    (remove-hook 'xref-backend-functions #'orgsyndb--xref-backend t)
    (remove-hook 'eldoc-documentation-functions #'orgsyndb-eldoc t)
    (remove-hook 'after-save-hook #'orgsyndb--after-save t)
    (orgsyndb--teardown-timestamps)
    (orgsyndb--teardown-diagnostics)
    (setq orgsyndb--root nil
          orgsyndb--kind nil)))

(defun orgsyndb--turn-on ()
  "Turn on `orgsyndb-mode' when the buffer visits a collection file."
  (when (and buffer-file-name (orgsyndb-file-kind buffer-file-name))
    (orgsyndb-mode 1)))

;;;###autoload
(define-globalized-minor-mode global-orgsyndb-mode orgsyndb-mode
  orgsyndb--turn-on
  :group 'orgsyndb)

;;;###autoload (autoload 'orgsyndb-dispatch "orgsyndb" nil t)
(transient-define-prefix orgsyndb-dispatch ()
  "Run a command of the OrgSynDB mode."
  [["Write"
    ("n" "New procedure" orgsyndb-new-procedure)
    ("c" "New compound" orgsyndb-new-compound)
    ("i" "Insert compound" orgsyndb-insert-compound)
    ("v" "Visit variant" orgsyndb-visit-variant)
    ("t" "Create translation" orgsyndb-create-translation)]
   ["Check"
    ("V" "Validate" orgsyndb-validate)
    ("r" "Refresh index" orgsyndb-refresh-index)
    ("s" "Structure window" orgsyndb-structure-mode)]
   ["Preview"
    ("p" "Preview page" orgsyndb-preview)
    ("S" "Serve site" orgsyndb-serve)
    ("k" "Stop server" orgsyndb-stop-server)
    ("a" "Build on save" orgsyndb-preview-on-save-mode)
    ("P" "PDF" orgsyndb-pdf)]])

(provide 'orgsyndb)

;;; orgsyndb.el ends here

;;; orgsyndb-flycheck.el --- Flycheck checker for collection files  -*- lexical-binding: t; -*-

;;; Commentary:

;; The Flycheck checker `orgsyndb', which reports the problems that the
;; Flymake backend `orgsyndb-flymake' reports.  It is defined once
;; Flycheck is loaded; loading this file loads neither.  Choose it with
;; `orgsyndb-diagnostics'.

;;; Code:

(require 'orgsyndb-check)

(declare-function flycheck-define-generic-checker "ext:flycheck"
                  (symbol docstring &rest properties))
(declare-function flycheck-error-new-at "ext:flycheck"
                  (line column &optional level message &rest properties))
(defvar flycheck-checkers)

(defconst orgsyndb-flycheck-modes
  '(org-mode markdown-mode gfm-mode markdown-ts-mode conf-toml-mode
             toml-ts-mode conf-mode conf-unix-mode text-mode fundamental-mode)
  "The major modes in which the checker `orgsyndb' may run.")

(defun orgsyndb-flycheck--start (checker callback)
  "Report the buffer's problems for CHECKER to Flycheck's CALLBACK."
  (funcall callback 'finished
           (mapcar (pcase-lambda (`(,line ,severity ,text))
                     (flycheck-error-new-at
                      line nil (if (equal severity "error") 'error 'warning)
                      text :checker checker))
                   (orgsyndb--buffer-problems))))

(with-eval-after-load 'flycheck
  (flycheck-define-generic-checker 'orgsyndb
    "The problems of an OrgSynDB collection file: the Org front end's
checks of an Org source and the problems of the last validation."
    :start #'orgsyndb-flycheck--start
    :modes orgsyndb-flycheck-modes
    :predicate (lambda () (bound-and-true-p orgsyndb-mode)))
  (when (boundp 'flycheck-checkers)
    (add-to-list 'flycheck-checkers 'orgsyndb)))

(provide 'orgsyndb-flycheck)

;;; orgsyndb-flycheck.el ends here

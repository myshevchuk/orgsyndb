;;; orgsyndb-stamp.el --- Modification times on save  -*- lexical-binding: t; -*-

;;; Commentary:

;; Keeps `#+LAST_MODIFIED' of an Org source and `lastmod' of a Markdown
;; procedure or sequence current with `time-stamp', through
;; buffer-local settings that leave the user's own `time-stamp'
;; settings in force everywhere else and give the buffer back its own
;; when the mode is turned off.

;;; Code:

(require 'orgsyndb-core)
(require 'time-stamp)

(defcustom orgsyndb-update-timestamps t
  "Non-nil means saving a procedure or sequence updates its modification
time, `#+LAST_MODIFIED' or `lastmod', in Europe/Berlin.
It is read at each save."
  :type 'boolean
  :group 'orgsyndb)

(defconst orgsyndb--stamp-variables
  '(time-stamp-active time-stamp-pattern time-stamp-start time-stamp-end
                      time-stamp-format time-stamp-time-zone
                      time-stamp-line-limit system-time-locale)
  "The variables that the mode gives buffer-local values.")

(defconst orgsyndb--stamp-clock "%Y-%02m-%02dT%02H:%02M:%02S"
  "The `time-stamp' format of a Markdown modification time, without its
offset.")

(defvar-local orgsyndb--stamp-saved nil
  "The buffer's own values of `orgsyndb--stamp-variables' while the mode
replaces them, each (VARIABLE) when it had no local value and
\(VARIABLE VALUE) when it had; nil while the mode replaces none.")

(defun orgsyndb--stamp-lines ()
  "Return the number of lines from the start of the buffer that may hold
its modification time, or nil when none may.
They are the lines before the first heading of an Org source, and the
front matter of a Markdown file."
  (save-excursion
    (save-restriction
      (widen)
      (goto-char (point-min))
      (if (eq orgsyndb--kind 'org-procedure)
          (let ((limit (if (re-search-forward "^\\*+[ \t]" nil t)
                           (1- (line-number-at-pos (match-beginning 0)))
                         (line-number-at-pos (point-max)))))
            (and (> limit 0) limit))
        (and (looking-at "\\+\\+\\+[ \t\r]*$")
             (progn (forward-line 1)
                    (re-search-forward "^\\+\\+\\+[ \t\r]*$" nil t))
             (line-number-at-pos (match-beginning 0)))))))

(defun orgsyndb--stamp-bind ()
  "Give the `time-stamp' variables the buffer's settings for a save now.
The buffer's own values are kept, the first time, in
`orgsyndb--stamp-saved'.  A Markdown time takes the Europe/Berlin
offset in force now, both as its fixed zone and as literal text of its
format."
  (unless orgsyndb--stamp-saved
    (setq orgsyndb--stamp-saved
          (mapcar (lambda (variable)
                    (if (local-variable-p variable)
                        (list variable (symbol-value variable))
                      (list variable)))
                  orgsyndb--stamp-variables)))
  (let ((lines (orgsyndb--stamp-lines)))
    (setq-local time-stamp-active (and lines t)
                time-stamp-pattern nil
                time-stamp-line-limit (or lines 1)
                system-time-locale "C"))
  (if (eq orgsyndb--kind 'org-procedure)
      (setq-local time-stamp-start
                  (concat "^[ \t]*#\\+[Ll][Aa][Ss][Tt]_"
                          "[Mm][Oo][Dd][Ii][Ff][Ii][Ee][Dd]:[ \t]*\\[")
                  time-stamp-end "\\]"
                  time-stamp-format "%Y-%02m-%02d %3a %02H:%02M:%02S"
                  time-stamp-time-zone osdb-org-zone)
    (let ((offset (car (current-time-zone (orgsyndb--now) osdb-org-zone))))
      (setq-local time-stamp-start "^lastmod[ \t]*=[ \t]*"
                  time-stamp-end "[ \t]*$"
                  time-stamp-time-zone offset
                  time-stamp-format (concat orgsyndb--stamp-clock
                                            (orgsyndb--offset-text offset))))))

(defun orgsyndb--stamp-restore ()
  "Give the buffer back its own values of the `time-stamp' variables."
  (pcase-dolist (`(,variable . ,own) orgsyndb--stamp-saved)
    (if own
        (set (make-local-variable variable) (car own))
      (kill-local-variable variable)))
  (setq orgsyndb--stamp-saved nil))

(defun orgsyndb--stamp-before-save ()
  "Update the buffer's modification time with `time-stamp', when
`orgsyndb-update-timestamps' is non-nil; otherwise give the buffer
back its own `time-stamp' settings."
  (if orgsyndb-update-timestamps
      (progn (orgsyndb--stamp-bind)
             (when time-stamp-active
               (time-stamp)))
    (orgsyndb--stamp-restore)))

(defun orgsyndb--setup-timestamps ()
  "Have each save of a procedure or sequence update its modification
time while `orgsyndb-update-timestamps' is non-nil."
  (when (memq orgsyndb--kind '(org-procedure md-procedure sequence))
    (when orgsyndb-update-timestamps
      (orgsyndb--stamp-bind))
    (add-hook 'before-save-hook #'orgsyndb--stamp-before-save -50 t)))

(defun orgsyndb--teardown-timestamps ()
  "Undo `orgsyndb--setup-timestamps'."
  (remove-hook 'before-save-hook #'orgsyndb--stamp-before-save t)
  (orgsyndb--stamp-restore))

(provide 'orgsyndb-stamp)

;;; orgsyndb-stamp.el ends here

;;; orgsyndb-stamp.el --- Modification times on save  -*- lexical-binding: t; -*-

;;; Commentary:

;; Keeps `#+LAST_MODIFIED' of an Org source and `lastmod' of a Markdown
;; procedure or sequence current with `time-stamp', through
;; buffer-local settings that leave the user's own `time-stamp'
;; settings in force everywhere else.

;;; Code:

(require 'orgsyndb-core)
(require 'time-stamp)

(defcustom orgsyndb-update-timestamps t
  "Non-nil means saving a procedure or sequence updates its modification
time, `#+LAST_MODIFIED' or `lastmod', in Europe/Berlin."
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

(defun orgsyndb--stamp-offset ()
  "Fix the buffer's `time-stamp' zone at the Europe/Berlin offset in
force now, and write that offset into its format."
  (let ((offset (car (current-time-zone (orgsyndb--now) osdb-org-zone))))
    (setq-local time-stamp-time-zone offset
                time-stamp-format (concat orgsyndb--stamp-clock
                                          (orgsyndb--offset-text offset)))))

(defun orgsyndb--setup-timestamps ()
  "Have saving update the buffer's modification time, when
`orgsyndb-update-timestamps' is non-nil and the buffer is a procedure
or sequence."
  (when (and orgsyndb-update-timestamps
             (memq orgsyndb--kind '(org-procedure md-procedure sequence)))
    (setq-local time-stamp-active t
                time-stamp-pattern nil
                time-stamp-line-limit 0
                system-time-locale "C")
    (if (eq orgsyndb--kind 'org-procedure)
        (setq-local time-stamp-start
                    (concat "^[ \t]*#\\+[Ll][Aa][Ss][Tt]_"
                            "[Mm][Oo][Dd][Ii][Ff][Ii][Ee][Dd]:[ \t]*\\[")
                    time-stamp-end "\\]"
                    time-stamp-format "%Y-%02m-%02d %3a %02H:%02M:%02S"
                    time-stamp-time-zone osdb-org-zone)
      (setq-local time-stamp-start "^lastmod[ \t]*=[ \t]*"
                  time-stamp-end "[ \t]*$")
      (orgsyndb--stamp-offset)
      (add-hook 'before-save-hook #'orgsyndb--stamp-offset -50 t))
    (add-hook 'before-save-hook #'time-stamp nil t)))

(defun orgsyndb--teardown-timestamps ()
  "Undo `orgsyndb--setup-timestamps'."
  (remove-hook 'before-save-hook #'orgsyndb--stamp-offset t)
  (remove-hook 'before-save-hook #'time-stamp t)
  (mapc #'kill-local-variable orgsyndb--stamp-variables))

(provide 'orgsyndb-stamp)

;;; orgsyndb-stamp.el ends here

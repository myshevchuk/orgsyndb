;;; orgsyndb-structure.el --- The structure of the compound at point  -*- lexical-binding: t; -*-

;;; Commentary:

;; `orgsyndb-structure-mode' shows, in a side window, the structure
;; image, name and formula of the compound at point.

;;; Code:

(require 'orgsyndb-xref)
(require 'image)

(defcustom orgsyndb-structure-delay 0.5
  "Seconds of idleness after which the structure window follows point."
  :type 'number
  :group 'orgsyndb)

(defconst orgsyndb--structure-buffer "*orgsyndb structure*"
  "The buffer of the structure window.")

(defvar-local orgsyndb--structure-timer nil
  "The idle timer that updates the structure window for this buffer.")

(defun orgsyndb--structure-compound ()
  "Return the compound key at point, or nil."
  (let ((identifier (orgsyndb--identifier-at-point)))
    (and identifier (not (string-match-p orgsyndb--id-regexp identifier))
         identifier)))

(defun orgsyndb--structure-file (root key)
  "Return the structure image of the compound KEY in ROOT, or nil.
That is the file `static/structures/KEY.svg' of the collection, or
`static/structures/KEY.png' when there is no SVG."
  (cl-find-if #'file-readable-p
              (mapcar (lambda (suffix)
                        (expand-file-name (concat key suffix)
                                          (expand-file-name
                                           "static/structures/" root)))
                      '(".svg" ".png"))))

(defun orgsyndb-structure-update ()
  "Show the compound at point in the structure buffer.
The buffer shows its structure image (`orgsyndb--structure-file'), when
it has one and Emacs can display the image's type, and below it its name
and formula.  When point is on no compound, the buffer keeps what it
shows."
  (when orgsyndb--root
    (let* ((root orgsyndb--root)
           (key (ignore-errors (orgsyndb--structure-compound)))
           (data (and key (orgsyndb--compound root key))))
      (when data
        (with-current-buffer (get-buffer-create orgsyndb--structure-buffer)
          (let* ((inhibit-read-only t)
                 (file (orgsyndb--structure-file root key))
                 (type (and file (image-supported-file-p file))))
            (erase-buffer)
            (when (and type (image-type-available-p type))
              (insert-image (create-image file type))
              (insert "\n\n"))
            (insert (or (alist-get 'name data) key) "\n"
                    (or (alist-get 'formula data) "") "\n")
            (goto-char (point-min))))))))

(defun orgsyndb--structure-schedule ()
  "Update the structure window once Emacs has been idle for
`orgsyndb-structure-delay' seconds."
  (when (timerp orgsyndb--structure-timer)
    (cancel-timer orgsyndb--structure-timer))
  (let ((buffer (current-buffer)))
    (setq orgsyndb--structure-timer
          (run-with-idle-timer orgsyndb-structure-delay nil
                               (lambda ()
                                 (when (buffer-live-p buffer)
                                   (with-current-buffer buffer
                                     (orgsyndb-structure-update))))))))

;;;###autoload
(define-minor-mode orgsyndb-structure-mode
  "Show the structure of the compound at point in a side window."
  :lighter nil
  (if orgsyndb-structure-mode
      (progn
        (display-buffer-in-side-window
         (get-buffer-create orgsyndb--structure-buffer)
         '((side . right) (window-width . 0.3)))
        (add-hook 'post-command-hook #'orgsyndb--structure-schedule nil t)
        (orgsyndb-structure-update))
    (remove-hook 'post-command-hook #'orgsyndb--structure-schedule t)
    (when (timerp orgsyndb--structure-timer)
      (cancel-timer orgsyndb--structure-timer))
    (let ((window (get-buffer-window orgsyndb--structure-buffer t)))
      (when (window-live-p window)
        (ignore-errors (delete-window window))))))

(provide 'orgsyndb-structure)

;;; orgsyndb-structure.el ends here

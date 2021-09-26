#!/usr/bin/env python3

"""Graphical webarchive extractor (requires Tkinter)."""

import os
import sys
import threading
import queue
import optparse

from glob import iglob

from tkinter import *
from tkinter.ttk import *
from tkinter.filedialog import askopenfilenames
from tkinter.messagebox import showerror

# userpaths is useful, but we can live without it
try: import userpaths
except (ImportError): userpaths = None

# Ditto for webbrowser
try: import webbrowser
except (ImportError): webbrowser = None

import webarchive


class ExtractorUI(Tk):
    """Extractor UI window."""

    def __init__(self, archives=[]):
        """Return a new ExtractorUI object."""

        Tk.__init__(self)
        self.title("Webarchive Extractor")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.close_window)

        # Archives to process
        self._archives = archives

        # To communicate with the ExtractorThread
        self._processing = BooleanVar()
        self._queue = None
        self._canceler = None

        # Whether to open the extracted file after processing
        # (only applicable if we are extracting a single archive)
        oa_var = self._open_after_processing = BooleanVar()

        if not archives:
            # Hide the window until we begin extraction
            self.withdraw()

        # --------------------------------------------------------------------

        # Progress display frame
        pf = self._progress_frame = Frame(self)
        pf.pack(side="top", expand=1, fill="both", padx=8, pady=8)

        # Archive name label
        an = self._archive_name = Label(pf)
        an.pack(side="top", fill="x")

        # Archive extraction progress
        ap = self._archive_progress = Progressbar(pf,
                                                  length=400)
        ap.pack(side="top", fill="x")

        # Resource name label
        rn = self._resource_name = Label(pf)
        rn.pack(side="top", fill="x", pady=(4, 0))

        # Resource extraction progress
        rp = self._resource_progress = Progressbar(pf,
                                                   length=400)
        rp.pack(side="top", fill="x")

        # --------------------------------------------------------------------

        # Separator
        sep = Separator(self)
        sep.pack(side="top", fill="x")

        # --------------------------------------------------------------------

        # Command button frame
        cf = self._command_frame = Frame(self)
        cf.pack(side="top", fill="x", padx=8, pady=8)

        # Close/Cancel button
        cb = self._close_button = Button(cf,
                                         text="Cancel",
                                         default="active",
                                         command=self.close_window)
        cb.pack(side="right")

        # "Open after processing" checkbox
        oa_label = "Open page after extracting"
        oa = self._open_after_checkbox = Checkbutton(cf,
                                                     text=oa_label,
                                                     variable=oa_var)
        oa.pack(side="left", padx=(0, 16))

        # --------------------------------------------------------------------

        # Key bindings
        for seq in "<Return>", "<Escape>", "<Control-w>", "<Control-q>":
            self.bind(seq, self.close_window)

        # --------------------------------------------------------------------

        if not self._archives:
            # Prompt for archives to process
            self.browse()

        if self._archives:
            # Determine whether we can open the page after processing
            if webbrowser and len(self._archives) == 1:
                self._open_after_processing.set(1)
            else:
                self._open_after_checkbox.configure(state="disabled")

            # Extract our archives
            self.extract_archives()

        else:
            # The user must have canceled the Browse dialog
            self.close_window()

    def browse(self, event=None):
        """Browse for archives to process."""

        filetypes = ("Webarchive Files", "*.webarchive"),

        if userpaths:
            # Start in the user's Downloads directory
            initialdir = userpaths.get_downloads()
        else:
            # Start in the current working directory
            initialdir = os.getcwd()

        archives = askopenfilenames(title="Open",
                                    filetypes=filetypes,
                                    initialdir=initialdir,
                                    parent=self)

        if archives:
            # Normalize path names
            self._archives = list(map(os.path.normpath, archives))

    def close_window(self, event=None):
        """Close the window."""

        if self._processing.get():
            # Cancel extraction
            self._canceler.set()
            self.wait_variable(self._processing)

        self.destroy()

    def extract_archives(self):
        """Extract the selected archives."""

        # Wait for any previous processing operation to finish
        if self._processing.get():
            self.wait_variable(self._processing)

        # Show the window if it was previously withdrawn
        self.deiconify()

        # Set the maximum archive extraction progress
        self._archive_progress.configure(maximum=len(self._archives))

        # Create a queue and canceler to communicate with the extractor thread
        self._queue = queue.Queue()
        self._canceler = threading.Event()

        # Create an ExtractorThread to extract the archives in the background
        et = ExtractorThread(self._archives, self._queue, self._canceler)
        et.start()

        # Start processing data from the queue
        self._processing.set(1)
        self._extract_archives_cb()

    def _extract_archives_cb(self):
        """Process data from the queue."""

        if not self._queue:
            return

        # Timeout in msec before resuming the loop
        timeout = 20
        error_occurred = False

        try:
            item = self._queue.get_nowait()

            if item is None:
                # Done processing
                self._processing.set(0)

            elif isinstance(item, Exception):
                # Halt processing and display the error message
                self._processing.set(0)
                showerror("Error", item, parent=self)
                error_occurred = True

            elif isinstance(item, tuple):
                # Interpret the message from the archive thread
                command, payload = item
                timeout = 0

                if command == "archive start":
                    # Display the archive name
                    label = "Archive: {0}".format(payload)
                    self._archive_name.configure(text=label)

                elif command == "archive done":
                    # Increment the archive extraction progress
                    self._archive_progress.step()

                elif command == "resource count":
                    # Set the maximum resource extraction progress
                    self._resource_progress.configure(maximum=payload)

                elif command == "resource start":
                    # Display the resource name
                    label = "Extracting: {0}".format(payload)
                    self._resource_name.configure(text=label)

                elif command == "resource done":
                    # Increment the resource extraction progress
                    self._resource_progress.step()

        except (queue.Empty):
            # Still waiting for the next item
            pass

        if self._processing.get():
            # Continue the loop until we're told to stop
            self.after(timeout, self._extract_archives_cb)

        else:
            # Clean up
            del self._queue
            del self._canceler
            self._queue = None
            self._canceler = None

            if (not error_occurred
                and webbrowser
                and self._open_after_processing.get()):
                # Figure out where we extracted this archive
                # FIXME: Duplicated from ExtractorThread.run()
                base, ext = os.path.splitext(self._archives[0])
                output_path = "{0}.html".format(base)

                # Open the extracted page
                webbrowser.open(output_path)

            # Close the window
            self.after(20, self.close_window)


class ExtractorThread(threading.Thread):
    """Webarchive extraction thread."""

    def __init__(self, archives, queue, canceler):
        """Return a new ExtractorThread object."""

        threading.Thread.__init__(self)

        self._archives = archives
        self._queue = queue
        self._canceler = canceler

    def run(self):
        """Extract the webarchives."""

        try:
            for archive_path in self._archives:
                if self._canceler.is_set():
                    break

                archive = webarchive.open(archive_path)
                archive_base = os.path.basename(archive_path)

                # Pass some information about the archive back to the UI
                self._queue.put(("archive start", archive_base))
                self._queue.put(("resource count", archive.resource_count()))

                # Derive the output path from the archive path
                base, ext = os.path.splitext(archive_path)
                output_path = "{0}.html".format(base)

                # Extract the archive
                archive.extract(output_path,
                                before_cb=self._before_cb,
                                after_cb=self._after_cb,
                                canceled_cb=self._canceler.is_set)
                self._queue.put(("archive done", archive_base))

            # Signal we are done processing
            self._queue.put(None)

        except (Exception) as err:
            # Pass the exception back to the UI thread
            self._queue.put(err)

    def _before_cb(self, res, output_path):
        """Callback before extracting a WebResource from an archive."""

        output_base = os.path.basename(output_path)
        self._queue.put(("resource start", output_base))

    def _after_cb(self, res, output_path):
        """Callback after extracting a WebResource from an archive."""

        self._queue.put(("resource done", None))


if __name__ == "__main__":
    parser = optparse.OptionParser(
        usage="%prog [options] input_path.webarchive [another.webarchive ...]",
        version="pywebarchive {0}".format(webarchive.__version__)
    )

    options, args = parser.parse_args()

    # Look for archives on the command line
    # If no archives are specified, ExtractorUI will display a browse dialog.
    archives = []
    for arg in args:
        archives += iglob(arg)

    ui = ExtractorUI(archives)
    ui.mainloop()

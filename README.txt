The Traxtile program was developed to allow interactive graphical review and revision of
object tracking assignments made with the CellProfiler TrackObjects module.

Python 2.7.x is required (earlier versions do not support dictionary comprehension and
Python 3.x and above require alternative syntax for some iteration operations).

To run, download the Python modules into a single directory, and sample data (often into
a subdirectory, but this is not necessary), and run 'traxtile.py' with the Python 2.7.x
interpreter.

See 'Traxtile User Manual.docx' for more information.

Components:
ImageViewer.py	Module for ‘whole image’ view
MontageFile.py	Module for import/export and reporting operations
MontageView.py	Module for main program interface
Trackmodel.py	Module for data model
traxtile.py	    Main program

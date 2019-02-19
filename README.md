# Tools for the Charmhigh Pick-and-Place Machine
Tools, scripts and instructions for efficient usage
of the Charmhigh Pick-and-Place Machine

## Quick start guide

* Load the machine with the required parts.
  You might want to create a CSV file which lists all the parts in the machine,
  with up to 5 columns (first two columns are required, others are optional):
  `part name | stack number | feed | head number | rotation offset`.

* Export the position file from KiCAD by opening Pcbnew, selecting
  `File -> Fabrication Outputs -> Footprint Position (.pos) File`,
  choosing an output directory and then clicking `Save Report File`.
  Don't forget to place the auxiliary axis origin
  in one of the corners of the PCB before generating the position file.
  This will later be used as the board origin when placing the parts.

* Use the python script `gen_charmhigh_pnp_file.py` to convert the position
  file to a DPV file used by the machine.
  Copy this file to USB stick.

* Apply solder paste to a PCB and place it in the machine.
  Be careful to place the corner of the board
  which was choosen as auxiliary axis origin in KiCAD
  in the lower left corner of the clamping mounts of the machine.

* Start the machine by toggling the power switch,
  then wait a few seconds and start the Charmhigh control program.

* Connect the USB stick.
  In the Charmhigh control program, click on `Files`, then on `Import`.
  Select the desired DPV file and then click on `Update` to import the file.

* In the main menu of the control program,
  click on `P` and then select the imported DPV file.
  Click on `Edit` and then on calibrate in order to calibrate the position
  of the PCB based on the fiducials or other marks.
  If the camera image does not show up, close the application and restart it.

* From the main menu click on `P`, again select the DPV file
  and then click on `Load`.

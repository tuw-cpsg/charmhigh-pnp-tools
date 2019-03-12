# Tools for the Charmhigh Pick-and-Place Machine
Tools, scripts and instructions for efficient usage
of the Charmhigh Pick-and-Place Machine

## Quick start guide

* Load the machine with the required parts.
  You might want to create a CSV file which lists all the parts in the machine,
  with up to 5 columns (first two columns are required, others are optional):
  ```
  part name | stack number | feed distance | head number | rotation offset
  ```
  For instance:
  ```
  100nF,1,2
  4u7F,18
  TPS65400-Q1,27,8,2,90
  ```
  Parts will be placed in the order in which they appear in this file.

* Export the position file from KiCAD by opening Pcbnew, selecting
  `File -> Fabrication Outputs -> Footprint Position (.pos) File`,
  choosing an output directory and then clicking `Save Report File`.
  Don't forget to place the auxiliary axis origin
  in one of the corners of the PCB before generating the position file.
  That corner will later be used as the board origin when placing the parts.

* Use the python script `gen_charmhigh_pnp_file.py` to convert the position
  file to a DPV file used by the machine, for instance by executing:
  ```
  gen_charmhigh_pnp_file.py --stackfile stack.csv -o out.dpv pos.csv
  ```
  where `stack.csv` is the name of the CSV file created in the first step,
  `pos.csv` is the position file exported from KiCAD
  and `out.dpv` selects a name for the machine file which shall be created.
  The option `-m` can be used to specify the coordinates of fiducials
  or other marks on the board
  which are later used to calibrate the position of the PCB in the machine.
  Copy the generated `*.dpv` file to a USB stick.

* Apply solder paste to a PCB and place it in the machine.
  Be careful to place the corner of the board
  which was choosen as auxiliary axis origin in KiCAD
  in the lower left corner of the clamping mounts of the machine.

* Start the machine by toggling the power switch,
  then wait a few seconds and start the Charmhigh control program.

* Connect the USB stick (in order for the USB stick to be recognized
  it must be connected **after** starting the Charmhigh control program).
  In the Charmhigh control program, click on `Files`, then on `Import`.
  Select the desired DPV file and then click on `Update` to import the file.

* In the main menu of the control program,
  click on `Run` and then select the imported DPV file.
  Click on `Edit` and then on `PCB calibrate` in order to calibrate the
  position of the PCB based on fiducials or other marks.
  If the camera image does not show up, close the Charmhigh control program
  and restart it **without turning of the machine**.

* From the main menu click on `Run`, again select the desired DPV file
  and then click on `Load`.
  The machine is now ready to start placing parts.
  By repeatedly clicking `Step` the machine slowly steps through the process.
  If you are very confident, you can click `Run`
  to have the machine quickly place all parts without interruption.

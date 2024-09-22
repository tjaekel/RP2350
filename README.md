# RP2350
 RP2350 sample code file

## Some RP2350 files
Using MicroPython and PIO on Rapsberry Pi Pico 2 (RP2350) in order
to implement some interfaces (via PIO), e.g.:
* MDIO
* BSTI
* QSPI
* SPI

## File:
* RP2350_SPI.py : a regular SPI peripheral for SPI master
* RP2350_PIO_SPI.py : a SPI master via PIO
* RP2350_PIO_MDIO.py : a MDIO interface (bi-directional DIO) with PIO and DIR signal (for level shifter)
* RP2350_PIO_BSTI.py : similar to MDIO but separated DIN and DOUT (no DIR signal needed)
* RP2350_PIO_QSPI.py : a QSPI master with 4 bi-directional lanes, DIR signal
* other files for testing GPIO, LED

## Boards:
These scripts are tested and used on:
* SparkFun Pro Micro - RP2350
* Pimoroni Pico Plus 2 (with RP2350)

## FPGA as level shifter
Using a Trenz GmbH FPGA board, TE0725-04-72I-1-B as level shifter board and for HW extensions.
Find the FPGA files in the sub-directory (for AMD/Xilinx Vivado 2023.2, an Artix 7 FPGA used as bi-directional level shifter, which needs a DIR signal to do so, therefore my bi-directional interfaces on RP2350 provide a DIR signal)


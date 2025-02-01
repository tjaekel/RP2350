## Configuration options, can be used for all designs
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
set_property BITSTREAM.CONFIG.CONFIGRATE 50 [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property CFGBVS VCCO [current_design]
set_property BITSTREAM.CONFIG.SPI_32BIT_ADDR YES [current_design]
set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]
set_property BITSTREAM.CONFIG.M1PIN PULLNONE [current_design]
set_property BITSTREAM.CONFIG.M2PIN PULLNONE [current_design]
set_property BITSTREAM.CONFIG.M0PIN PULLNONE [current_design]

set_property BITSTREAM.CONFIG.USR_ACCESS TIMESTAMP [current_design]

##Clock
create_clock -period 10 -waveform {0 5} [get_ports SYS_CLOCK]
set_property PACKAGE_PIN P17 [get_ports SYS_CLOCK]
set_property IOSTANDARD LVCMOS33 [get_ports SYS_CLOCK]

##LED
set_property PACKAGE_PIN M16 [get_ports LED]
set_property IOSTANDARD LVCMOS33 [get_ports LED]

##I/Os - bank 34 - 3V3 always:
set_property PACKAGE_PIN N5 [get_ports P2_QCLK]
set_property IOSTANDARD LVCMOS33 [get_ports P2_QCLK]
set_property PACKAGE_PIN U2 [get_ports P2_QD0]
set_property IOSTANDARD LVCMOS33 [get_ports P2_QD0]
set_property PACKAGE_PIN U4 [get_ports P2_QD1]
set_property IOSTANDARD LVCMOS33 [get_ports P2_QD1]
set_property PACKAGE_PIN T6 [get_ports P2_QD2]
set_property IOSTANDARD LVCMOS33 [get_ports P2_QD2]
set_property PACKAGE_PIN N6 [get_ports P2_QD3]
set_property IOSTANDARD LVCMOS33 [get_ports P2_QD3]
set_property PACKAGE_PIN P4 [get_ports P2_CSn]
set_property IOSTANDARD LVCMOS33 [get_ports P2_CSn]
set_property PACKAGE_PIN T4 [get_ports P2_CSn2]
set_property IOSTANDARD LVCMOS33 [get_ports P2_CSn2]
set_property PACKAGE_PIN U1 [get_ports P2_QDIR]
set_property IOSTANDARD LVCMOS33 [get_ports P2_QDIR]
##QCLK feedback
set_property PACKAGE_PIN R3 [get_ports P2_QCLKout]
set_property IOSTANDARD LVCMOS33 [get_ports P2_QCLKout]

set_property PACKAGE_PIN M2 [get_ports DLED]
set_property IOSTANDARD LVCMOS33 [get_ports DLED]

##I/Os - bank 34 - VCC2:
set_property PACKAGE_PIN F4 [get_ports QCLK]
set_property IOSTANDARD LVCMOS33 [get_ports QCLK]
set_property PACKAGE_PIN D2 [get_ports QD0]
set_property IOSTANDARD LVCMOS33 [get_ports QD0]
set_property PACKAGE_PIN K2 [get_ports QD1]
set_property IOSTANDARD LVCMOS33 [get_ports QD1]
set_property PACKAGE_PIN H2 [get_ports QD2]
set_property IOSTANDARD LVCMOS33 [get_ports QD2]
set_property PACKAGE_PIN G2 [get_ports QD3]
set_property IOSTANDARD LVCMOS33 [get_ports QD3]
set_property PACKAGE_PIN K1 [get_ports CSn]
set_property IOSTANDARD LVCMOS33 [get_ports CSn]
set_property PACKAGE_PIN F3 [get_ports CSn2]
set_property IOSTANDARD LVCMOS33 [get_ports CSn2]
##QCLK feedback
set_property PACKAGE_PIN C7 [get_ports QCLKout]
set_property IOSTANDARD LVCMOS33 [get_ports QCLKout]
set_property PACKAGE_PIN A5 [get_ports QCLKin]
set_property IOSTANDARD LVCMOS33 [get_ports QCLKin]


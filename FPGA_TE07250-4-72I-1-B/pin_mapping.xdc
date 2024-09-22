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

##I/Os
set_property PACKAGE_PIN P5 [get_ports IN0]
set_property IOSTANDARD LVCMOS33 [get_ports IN0]
set_property PULLUP TRUE [get_ports IN0]

set_property PACKAGE_PIN C6 [get_ports OUT0]
set_property IOSTANDARD LVCMOS33 [get_ports OUT0]

set_property PACKAGE_PIN M1 [get_ports DIOA]
set_property IOSTANDARD LVCMOS33 [get_ports DIOA]

set_property PACKAGE_PIN C5 [get_ports DIOB]
set_property IOSTANDARD LVCMOS33 [get_ports DIOB]

set_property PACKAGE_PIN B7 [get_ports DIR]
set_property IOSTANDARD LVCMOS33 [get_ports DIR]
set_property PULLUP TRUE [get_ports DIR]

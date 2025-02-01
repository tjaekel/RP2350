----------------------------------------------------------------------------------
-- Company: 
-- Engineer: 
-- 
-- Create Date: 09/18/2024 03:57:39 PM
-- Design Name: 
-- Module Name: FPGA_top - Behavioral
-- Project Name: 
-- Target Devices: /
-- Tool Versions: 
-- Description: 
-- 
-- Dependencies: 
-- 
-- Revision:
-- Revision 0.01 - File Created
-- Additional Comments:
-- 
----------------------------------------------------------------------------------

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_unsigned.all;

-- Uncomment the following library declaration if using
-- arithmetic functions with Signed or Unsigned values
-- use IEEE.NUMERIC_STD.ALL;

-- Uncomment the following library declaration if instantiating
-- any Xilinx leaf cells in this code.
library UNISIM;
use UNISIM.VComponents.all;

entity FPGA_top is
    Port ( SYS_CLOCK : in STD_LOGIC;
           -- Pico2 bank34:
           P2_QCLK   : in STD_LOGIC;
           P2_QD0    : inout STD_LOGIC;
           P2_QD1    : inout STD_LOGIC;
           P2_QD2    : inout STD_LOGIC;
           P2_QD3    : inout STD_LOGIC;
           P2_QDIR   : in STD_LOGIC;
           P2_CSn    : in STD_LOGIC;
           P2_CSn2   : in STD_LOGIC;
           
           P2_QCLKout : out STD_LOGIC;
           
           -- IO pins bank 35:         
           QCLK      : out STD_LOGIC;
           QD0       : inout STD_LOGIC;
           QD1       : inout STD_LOGIC;
           QD2       : inout STD_LOGIC;
           QD3       : inout STD_LOGIC;
           CSn       : out STD_LOGIC;
           CSn2      : out STD_LOGIC;
           
           QCLKout   : out STD_LOGIC;
           QCLKin    : in STD_LOGIC;
           
           -- Dual LED on PCB, bak 34:
           DLED : out STD_LOGIC;
           
           -- onboard LED
           LED  : out STD_LOGIC);
end FPGA_top;

architecture Behavioral of FPGA_top is
    signal Pre_Q: std_logic_vector(28 downto 0) := (others=>'0');
    signal led_int: std_logic;
    signal led_oe: std_logic;
    --signal mdio_in : std_logic;
    --signal mdio_out : std_logic;
begin

    -- use tri-state output buffer for PCB LED
    --OBUFT_dled : OBUFT
    --generic map (
    --    DRIVE => 12,
    --    IOSTANDARD => "DEFAULT",
    --    SLEW => "SLOW")
    --port map (
    --    O => DLED,
    --    I => led_int,
    --    T => led_oe);
    -- actually, easier to write:
    DLED <= 'Z' when led_oe = '1' else led_int;
        
    -- use 100MHz external clock
    process(SYS_CLOCK)
    begin
	if (rising_edge(SYS_CLOCK)) then
		Pre_Q <= Pre_Q + 1;
	end if;
    end process;
    
    led_int <= Pre_Q(27);
    led_oe  <= Pre_Q(28);
    
    LED <= led_int;
    
    --map QSPI signals
    --P2_QDIR = 1 for READ on Pico2, 0 = WRITE from PICO2
    QCLK    <= P2_QCLK;
    QD0     <= P2_QD0 when P2_QDIR = '0' else 'Z';   --WRITE
    P2_QD0  <= QD0 when P2_QDIR = '1' else 'Z';      --READ
    QD1     <= P2_QD1 when P2_QDIR = '0' else 'Z';   --WRITE
    P2_QD1  <= QD1 when P2_QDIR = '1' else 'Z';      --READ
    QD2     <= P2_QD2 when P2_QDIR = '0' else 'Z';   --WRITE
    P2_QD2  <= QD2 when P2_QDIR = '1' else 'Z';      --READ
    QD3     <= P2_QD3 when P2_QDIR = '0' else 'Z';   --WRITE
    P2_QD3  <= QD3 when P2_QDIR = '1' else 'Z';      --READ
    CSn     <= P2_CSn;
    CSn2    <= P2_CSn2;
    
    --QCLK feedback
    QCLKout <= P2_QCLK;
    P2_QCLKout <= QCLKin;
    
end Behavioral;

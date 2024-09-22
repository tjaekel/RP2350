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
--library UNISIM;
--use UNISIM.VComponents.all;

entity FPGA_top is
    Port ( SYS_CLOCK : in STD_LOGIC;
           IN0  : in STD_LOGIC;
           OUT0 : out STD_LOGIC;
           LED  : out STD_LOGIC;
           DIOA : inout STD_LOGIC;
           DIOB : inout STD_LOGIC;
           DIR  : in STD_LOGIC);
end FPGA_top;

architecture Behavioral of FPGA_top is
    signal Pre_Q: std_logic_vector(27 downto 0) := (others=>'0');
begin
    OUT0 <= IN0;

    process(SYS_CLOCK)
    begin
	if (rising_edge(SYS_CLOCK)) then
		Pre_Q <= Pre_Q + 1;
	end if;
    end process;
    
    LED <= Pre_Q(27) and IN0;
    
    DIOB <= DIOA when DIR = '1' else 'Z';
    DIOA <= DIOB when DIR = '0' else 'Z';
    
end Behavioral;

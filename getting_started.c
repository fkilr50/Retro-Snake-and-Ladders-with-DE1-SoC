#include <stdint.h>
#include <stdbool.h>

#define KEY_BASE       0xFF200050
#define HEX5_4_BASE    0xFF200030
#define HEX3_0_BASE    0xFF200020  // Address for HEX3, HEX2, HEX1, HEX0
#define UART0_BASE     0xFFC02000

volatile int * KEY_ptr      = (int *) KEY_BASE;
volatile int * HEX_ptr      = (int *) HEX3_0_BASE;
volatile int * HEX5_4_ptr      = (int *) HEX5_4_BASE;
volatile int * UART0_DATA_ptr = (int *) UART0_BASE;
volatile int * UART0_LSR_ptr  = (int *) (UART0_BASE + 0x14); 

// UART Setup pointers
volatile int * UART0_LCR_ptr  = (int *) (UART0_BASE + 0x0C); 
volatile int * UART0_DLL_ptr  = (int *) (UART0_BASE + 0x00); 
volatile int * UART0_DLH_ptr  = (int *) (UART0_BASE + 0x04); 

// 7-Segment Patterns (0-6)
unsigned char hex_table[] = {
    0x3F, // 0
    0x06, // 1
    0x5B, // 2
    0x4F, // 3
    0x66, // 4
    0x6D, // 5
    0x7D, // 6
    0x07, // 7
    0x7F, // 8
    0x6F  // 9
};

void UART_init() {
    *UART0_LCR_ptr = 0x83; 
    *UART0_DLL_ptr = 0x36; 
    *UART0_DLH_ptr = 0x00;
    *UART0_LCR_ptr = 0x03; 
}

void UART_send(char c) {
    while (!((*UART0_LSR_ptr) & 0x20)); 
    *UART0_DATA_ptr = c;
}

int UART_has_data() {
    return (*UART0_LSR_ptr) & 0x01;
}

char UART_read() {
    return (char)(*UART0_DATA_ptr & 0xFF);
}


int main(void) {
    UART_init();
    int ten1 = 0;
    int unit1 = 0;
    int ten2 = 0;
    int unit2 = 0;
    *HEX_ptr = 0; // Clear HEX displays at start
    *HEX5_4_ptr = 0;
    
    while (1) {
        // --- PART 1: SEND TO PYTHON (Buttons) ---
        int key_val = *(KEY_ptr) & 0xF; 
        if (key_val != 0) {
            if (key_val & 0x1) 
                UART_send('1'); // Signal Python to roll
            else if (key_val & 0x8) {   // KEY 1 (Restart)
                UART_send('2');         // Send '2' to Python
                uint32_t pattern30 = (hex_table[0] << 16) | (hex_table[0] << 8) | hex_table[0];
                *HEX_ptr = pattern30;
                uint32_t pattern54 = (hex_table[0] << 8) | hex_table[0];
                *HEX5_4_ptr = pattern54;
                ten1 = 0;
                unit1 = 0;
                ten2 = 0;
                unit2 = 0;
                printf("BOARD RESTARTED\n");
            }
            else if (key_val & 0x2) UART_send('3'); // PvP Mode
            else if (key_val & 0x4) UART_send('4'); // AI Mode
            while (*(KEY_ptr) != 0); // Wait for release
        }

        // --- PART 2: RECEIVE FROM PYTHON (Dice Result) ---
        if (UART_has_data()) {
            unsigned char header = UART_read();

            if (header == 0xFF) {
                // Now we know for sure the next 4 bytes are our data
                while (!UART_has_data()); // Wait for Byte 1
                int roll   = UART_read();
                
                while (!UART_has_data()); // Wait for Byte 2
                int p_num  = UART_read();
                
                while (!UART_has_data()); // Wait for Byte 3
                int tens   = UART_read();
                
                while (!UART_has_data()); // Wait for Byte 4
                int units  = UART_read();

                if(p_num == 1){
                    ten1 = tens;
                    unit1 = units;
                } 
                else {
                    ten2 = tens;
                    unit2 = units; 
                }

                // Applying LED
                uint32_t pattern30 = (hex_table[roll] << 16) | (hex_table[ten1] << 8) | hex_table[unit1];
                *HEX_ptr = pattern30;
                uint32_t pattern54 = (hex_table[ten2] << 8) | hex_table[unit2];
                *HEX5_4_ptr = pattern54;
                printf("PACKET RECV -> P%d | Roll: %d | Pos: %d%d\n", p_num, roll, tens, units);
            }
        }
    }
    return 0;
}
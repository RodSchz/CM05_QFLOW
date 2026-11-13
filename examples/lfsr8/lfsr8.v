// LFSR de 8 bits (x^8 + x^6 + x^5 + x^4 + 1), reset sincrono
module lfsr8 (input clk, input rst, input en, output reg [7:0] q);
  wire fb = q[7] ^ q[5] ^ q[4] ^ q[3];
  always @(posedge clk)
    if (rst)     q <= 8'h01;
    else if (en) q <= {q[6:0], fb};
endmodule

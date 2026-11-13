// Contador de 4 bits con reset SINCRONO (CM05 aun no tiene DFF con reset asincrono)
module counter (input clk, input rst, input en, output reg [3:0] q);
  always @(posedge clk)
    if (rst)     q <= 4'd0;
    else if (en) q <= q + 4'd1;
endmodule

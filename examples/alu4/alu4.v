// ALU combinacional de 4 bits
module alu4 (input [3:0] a, input [3:0] b, input [1:0] op, output reg [3:0] y, output reg c);
  always @* begin
    c = 1'b0;
    case (op)
      2'b00: {c, y} = a + b;
      2'b01: {c, y} = a - b;
      2'b10: y = a & b;
      2'b11: y = a ^ b;
    endcase
  end
endmodule

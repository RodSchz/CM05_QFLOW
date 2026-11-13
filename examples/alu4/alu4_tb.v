// Testbench exhaustivo de la ALU de 4 bits: 4 operaciones x 256 combinaciones
`timescale 1ns/1ps
module tb;
  reg  [3:0] a, b;
  reg  [1:0] op;
  wire [3:0] y;
  wire       c;
  reg  [4:0] esp;
  integer i, errores = 0;

  alu4 dut (.a(a), .b(b), .op(op), .y(y), .c(c));

  initial begin
    $dumpfile("sim.vcd"); $dumpvars(0, tb);
    for (i = 0; i < 1024; i = i + 1) begin
      {op, a, b} = i;
      #10;
      case (op)
        2'b00: esp = a + b;
        2'b01: esp = {1'b0, a} - {1'b0, b};
        2'b10: esp = {1'b0, a & b};
        2'b11: esp = {1'b0, a ^ b};
      endcase
      if (i % 61 == 0) $display("op=%b a=%0d b=%0d -> y=%0d c=%b", op, a, b, y, c);
      if ({c, y} !== esp) begin
        errores = errores + 1;
        if (errores < 5) $display("  ERROR op=%b a=%0d b=%0d: %b%b esperado %b", op, a, b, c, y, esp);
      end
    end
    if (errores == 0) $display("RESULTADO: OK (1024 vectores)");
    else              $display("RESULTADO: %0d ERRORES", errores);
    $finish;
  end
endmodule

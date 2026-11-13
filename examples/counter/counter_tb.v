// Testbench del contador de 4 bits: compara contra un modelo de referencia
`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, en = 0;
  wire [3:0] q;
  reg  [3:0] ref_q;
  integer errores = 0, ciclo;

  counter dut (.clk(clk), .rst(rst), .en(en), .q(q));

  always #50 clk = ~clk;                  // reloj de 10 MHz

  always @(posedge clk)                   // modelo de referencia
    if (rst) ref_q <= 0; else if (en) ref_q <= ref_q + 1;

  initial begin
    $dumpfile("sim.vcd"); $dumpvars(0, tb);
    for (ciclo = 0; ciclo < 40; ciclo = ciclo + 1) begin
      @(negedge clk);
      rst = (ciclo < 2) || (ciclo == 30);   // reset al inicio y a mitad
      en  = (ciclo % 7) != 3;               // pausa de vez en cuando
      if (ciclo > 2) begin
        $display("ciclo=%0d rst=%b en=%b q=%0d", ciclo, rst, en, q);
        if (q !== ref_q) begin errores = errores + 1; $display("  ERROR: esperado %0d", ref_q); end
      end
    end
    if (errores == 0) $display("RESULTADO: OK (37 ciclos verificados)");
    else              $display("RESULTADO: %0d ERRORES", errores);
    $finish;
  end
endmodule

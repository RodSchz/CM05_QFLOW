// Testbench del LFSR de 8 bits: verifica la secuencia y su periodo maximo (255)
`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, en = 0;
  wire [7:0] q;
  reg  [7:0] ref_q;
  integer errores = 0, ciclo, periodo = 0;

  lfsr8 dut (.clk(clk), .rst(rst), .en(en), .q(q));

  always #50 clk = ~clk;

  always @(posedge clk)
    if (rst) ref_q <= 8'h01;
    else if (en) ref_q <= {ref_q[6:0], ref_q[7] ^ ref_q[5] ^ ref_q[4] ^ ref_q[3]};

  initial begin
    $dumpfile("sim.vcd"); $dumpvars(0, tb);
    @(negedge clk); @(negedge clk);
    rst = 0; en = 1;
    for (ciclo = 0; ciclo < 260; ciclo = ciclo + 1) begin
      @(negedge clk);
      if (ciclo < 16) $display("ciclo=%0d q=%h", ciclo, q);
      if (q !== ref_q) errores = errores + 1;
      if (q == 8'h01 && periodo == 0) periodo = ciclo + 1;
    end
    $display("periodo=%0d", periodo);
    if (errores == 0 && periodo == 255) $display("RESULTADO: OK (periodo 255)");
    else $display("RESULTADO: %0d ERRORES (periodo %0d)", errores, periodo);
    $finish;
  end
endmodule

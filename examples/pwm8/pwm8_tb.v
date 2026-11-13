// Testbench del PWM de 8 bits: mide el ciclo de trabajo para varios valores de duty
`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1;
  reg  [7:0] duty = 0;
  wire out;
  integer altos, k, n, errores = 0;
  reg [7:0] duties [0:4];

  pwm8 dut (.clk(clk), .rst(rst), .duty(duty), .out(out));

  always #50 clk = ~clk;

  initial begin
    $dumpfile("sim.vcd"); $dumpvars(0, tb);
    duties[0] = 0; duties[1] = 1; duties[2] = 64; duties[3] = 128; duties[4] = 200;
    @(negedge clk); @(negedge clk); rst = 0;
    for (k = 0; k < 5; k = k + 1) begin
      duty = duties[k];
      repeat (256) @(negedge clk);          // un periodo para estabilizar
      altos = 0;
      for (n = 0; n < 256; n = n + 1) begin @(negedge clk); altos = altos + out; end
      $display("duty=%0d -> ciclos en alto=%0d de 256", duty, altos);
      if (altos != duty) errores = errores + 1;
    end
    if (errores == 0) $display("RESULTADO: OK (5 valores de duty)");
    else              $display("RESULTADO: %0d ERRORES", errores);
    $finish;
  end
endmodule

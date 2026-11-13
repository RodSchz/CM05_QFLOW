// PWM de 8 bits con contador libre y comparador, reset sincrono
module pwm8 (input clk, input rst, input [7:0] duty, output reg out);
  reg [7:0] cnt;
  always @(posedge clk) begin
    if (rst) begin cnt <= 8'd0; out <= 1'b0; end
    else begin cnt <= cnt + 8'd1; out <= (cnt < duty); end
  end
endmodule

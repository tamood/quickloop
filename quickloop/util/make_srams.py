#! /usr/bin/env python

# See LICENSE.SiFive for license details.
# See LICENSE.Berkeley for license details.

import sys
import math

blackbox = 0

def parse_line(line):
  name = ''
  width = 0
  depth = 0
  ports = ''
  mask_gran = 0
  tokens = line.split()
  i = 0
  for i in range(0,len(tokens),2):
    s = tokens[i]
    if s == 'name':
      name = tokens[i+1]
    elif s == 'width':
      width = int(tokens[i+1])
      mask_gran = width # default setting
    elif s == 'depth':
      depth = int(tokens[i+1])
    elif s == 'ports':
      ports = tokens[i+1].split(',')
    elif s == 'mask_gran':
      mask_gran = int(tokens[i+1])
    else:
      sys.exit('%s: unknown argument %s' % (sys.argv[0], a))
  return (name, width, depth, mask_gran, width//mask_gran, ports)

def gen_mem(name, width, depth, mask_gran, mask_seg, ports):
  addr_width = max(math.ceil(math.log(depth)/math.log(2)),1)
  port_spec = []
  readports = []
  writeports = []
  rwports = []
  decl = []
  combinational = []
  sequential = []
  maskedports = {}
  for pid in range(len(ports)):
    ptype = ports[pid]
    if ptype[0:1] == 'm':
      ptype = ptype[1:]
      maskedports[pid] = pid

    if ptype == 'read':
      prefix = 'R%d_' % len(readports)
      port_spec.append('input %sclk' % prefix)
      port_spec.append('input [%d:0] %saddr' % (addr_width-1, prefix))
      port_spec.append('input %sen' % prefix)
      port_spec.append('output [%d:0] %sdata' % (width-1, prefix))
      readports.append(pid)
    elif ptype == 'write':
      prefix = 'W%d_' % len(writeports)
      port_spec.append('input %sclk' % prefix)
      port_spec.append('input [%d:0] %saddr' % (addr_width-1, prefix))
      port_spec.append('input %sen' % prefix)
      port_spec.append('input [%d:0] %sdata' % (width-1, prefix))
      if pid in maskedports:
        port_spec.append('input [%d:0] %smask' % (mask_seg-1, prefix))
      writeports.append(pid)
    elif ptype == 'rw':
      prefix = 'RW%d_' % len(rwports)
      port_spec.append('input %sclk' % prefix)
      port_spec.append('input [%d:0] %saddr' % (addr_width-1, prefix))
      port_spec.append('input %sen' % prefix)
      port_spec.append('input %swmode' % prefix)
      if pid in maskedports:
        port_spec.append('input [%d:0] %swmask' % (mask_seg-1, prefix))
      port_spec.append('input [%d:0] %swdata' % (width-1, prefix))
      port_spec.append('output [%d:0] %srdata' % (width-1, prefix))
      rwports.append(pid)
    else:
      sys.exit('%s: unknown port type %s' % (sys.argv[0], ptype))

  for i in range(mask_seg):
    decl.append('reg [%d:0] ram%d [%d:0];' % (mask_gran-1, i, depth-1))

  for idx in range(len(readports)):
    prefix = ('R%d_') % idx
    decl.append('reg [%d:0] reg_%saddr;' % (addr_width-1, prefix))
    sequential.append('always @(posedge %sclk) begin' % prefix)
    sequential.append('  if (%sen) reg_%saddr <= %saddr;' % (prefix, prefix, prefix))
    sequential.append('end')
    for i in range(mask_seg):
      ram_range = '%d:%d' % ((i+1)*mask_gran-1, i*mask_gran)
      combinational.append('assign %sdata[%s] = ram%d[reg_%saddr];' % (prefix, ram_range, i, prefix))

  for idx in range(len(writeports)):
    pid = writeports[idx]
    prefix = 'W%d_' % idx
    sequential.append('always @(posedge %sclk) begin' % prefix)
    sequential.append("  if (%sen) begin" % prefix)
    for i in range(mask_seg):
      mask = ('if (%smask[%d]) ' % (prefix, i)) if pid in maskedports else ''
      ram_range = '%d:%d' % ((i+1)*mask_gran-1, i*mask_gran)
      sequential.append("    %sram%d[%saddr] <= %sdata[%s];" % (mask, i, prefix, prefix, ram_range))
    sequential.append("  end")
    sequential.append('end')

  for idx in range(len(rwports)):
    pid = rwports[idx]
    prefix = 'RW%d_' % idx
    decl.append("reg [%d:0] reg_%saddr;" % (addr_width-1, prefix))
    sequential.append("always @(posedge %sclk) begin" % prefix)
    sequential.append("  if (%sen) begin" % (prefix))
    sequential.append("    if (%swmode) begin" % (prefix))
    for i in range(mask_seg):
      mask = ('if (%swmask[%d]) ' % (prefix, i)) if pid in maskedports else ''
      ram_range = '%d:%d' % ((i+1)*mask_gran-1, i*mask_gran)
      sequential.append("      %sram%d[%saddr] <= %swdata[%s];" % (mask, i, prefix, prefix, ram_range))
      combinational.append("assign %srdata[%s] = ram%d[reg_%saddr];" % (prefix, ram_range, i, prefix))
    sequential.append("    end else begin")
    sequential.append("      reg_%saddr <= %saddr;" % (prefix, prefix))
    sequential.append("    end")
    sequential.append("  end")
    sequential.append("end")

  body = "\
  %s\n\n\
  %s\n\n\
  %s\n" % ('\n  '.join(decl), '\n  '.join(combinational), '\n  '.join(sequential))

  s = "\nmodule %s(\n\
  %s\n\
);\n\
\n\
%s\
\n\
endmodule" % (name, ',\n  '.join(port_spec), body if not blackbox else "")

  return s

def MakeSRAM(conf_file, output_file):
  f = open(output_file, "w")
  for line in open(conf_file):
    parsed_line = gen_mem(*parse_line(line))
    f.write(parsed_line)
  f.close()


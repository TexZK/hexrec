#!/bin/sh

hexdump -c bytes.bin > test_hexdump_-c_bytes.bin.hexdump
hexdump -C bytes.bin > test_hexdump_-C__bytes.bin.hexdump
hexdump -d bytes.bin > test_hexdump_-d_bytes.bin.hexdump
hexdump -n 128 bytes.bin > test_hexdump_-n_128_bytes.bin.hexdump
hexdump -o bytes.bin > test_hexdump_-o_bytes.bin.hexdump
hexdump -s 128 -n 64 bytes.bin > test_hexdump_-s_128_-n_64_bytes.bin.hexdump
hexdump -s 32 bytes.bin > test_hexdump_-s_32_bytes.bin.hexdump
# hexdump -U bytes.bin > test_hexdump_-U_bytes.bin.hexdump  # custom
hexdump -v wildcard.bin > test_hexdump_-v_wildcard.bin.hexdump
hexdump -x bytes.bin > test_hexdump_-x_bytes.bin.hexdump
# hexdump -X bytes.bin > test_hexdump_-X__bytes.bin.hexdump  # custom
hexdump bytes.bin > test_hexdump_bytes.bin.hexdump
hexdump wildcard.bin > test_hexdump_wildcard.bin.hexdump

alias hd="hexdump -C"
hd -b bytes.bin > test_hd_-b_bytes.bin.hd
hd -c bytes.bin > test_hd_-c_bytes.bin.hd
hd -d bytes.bin > test_hd_-d_bytes.bin.hd
hd -n 128 bytes.bin > test_hd_-n_128_bytes.bin.hd
hd -o bytes.bin > test_hd_-o_bytes.bin.hd
hd -s 128 -n 64 bytes.bin > test_hd_-s_128_-n_64_bytes.bin.hd
hd -s 32 bytes.bin > test_hd_-s_32_bytes.bin.hd
# hd -U bytes.bin > test_hd_-U_bytes.bin.hd  # custom
hd -v wildcard.bin > test_hd_-v_wildcard.bin.hd
hd -x bytes.bin > test_hd_-x_bytes.bin.hd
# hd -X bytes.bin > test_hd_-X__bytes.bin.hd  # custom
hd bytes.bin > test_hd_bytes.bin.hd
hd wildcard.bin > test_hd_wildcard.bin.hd

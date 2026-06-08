package main

import "testing"

func TestPlaceholderMessage(t *testing.T) {
	if got := placeholderMessage(); got != "dhcp-apply-helper scaffold only" {
		t.Fatalf("unexpected placeholder message: %q", got)
	}
}

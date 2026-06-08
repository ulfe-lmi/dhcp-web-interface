package main

import "testing"

func TestPlaceholderMessage(t *testing.T) {
	if got := placeholderMessage(); got != "dhcp-agent scaffold only" {
		t.Fatalf("unexpected placeholder message: %q", got)
	}
}

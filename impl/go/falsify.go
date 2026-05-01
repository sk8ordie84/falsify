// Package main — falsify-go: third reference implementation of PRML v0.1.
//
// Single-file Go implementation. Standard library only.
// Reproduces all 12 PRML v0.1 conformance vectors byte-for-byte.
//
// Spec:    https://spec.falsify.dev/v0.1
// Vectors: https://github.com/sk8ordie84/falsify/tree/main/spec/test-vectors
// Python:  https://github.com/sk8ordie84/falsify (reference implementation)
// JS:      https://github.com/sk8ordie84/falsify/tree/main/impl/js (second)
//
// Usage:
//
//	falsify-go test-vectors <vectors.json>    run conformance suite
//	falsify-go hash <spec.json>               print canonical SHA-256 only
//	falsify-go verify <spec.json> --observed <v>   verify hash; if --observed, evaluate
//
// License: MIT.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

// ─────────────────────────────────────────────────────────────────────────
// Canonicalization
// ─────────────────────────────────────────────────────────────────────────

// yamlIndicators are characters that, when at the start of a string, force
// PyYAML to quote it. We match PyYAML's behaviour to reproduce its bytes.
var yamlIndicators = map[byte]bool{
	'?': true, ':': true, ',': true, '[': true, ']': true,
	'{': true, '}': true, '#': true, '&': true, '*': true,
	'!': true, '|': true, '>': true, '\'': true, '"': true,
	'%': true, '@': true, '`': true,
}

// plainBoolNullSet contains strings that look like bool/null and would be
// re-resolved by a YAML 1.1 parser if left unquoted.
var plainBoolNullSet = map[string]bool{
	"y": true, "Y": true, "yes": true, "Yes": true, "YES": true,
	"n": true, "N": true, "no": true, "No": true, "NO": true,
	"true": true, "True": true, "TRUE": true,
	"false": true, "False": true, "FALSE": true,
	"on": true, "On": true, "ON": true,
	"off": true, "Off": true, "OFF": true,
	"null": true, "Null": true, "NULL": true,
	"~": true, "": true,
}

// numberRegexes — strings matching any of these would be parsed as numbers
// in YAML 1.1 plain-scalar resolution and therefore need quoting.
var (
	floatRegex     = regexp.MustCompile(`^[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?$`)
	intRegex       = regexp.MustCompile(`^[-+]?[0-9]+$`)
	hexRegex       = regexp.MustCompile(`^[-+]?0[xX][0-9a-fA-F]+$`)
	octalRegex     = regexp.MustCompile(`^[-+]?0[oO]?[0-7]+$`)
	infRegex       = regexp.MustCompile(`^[-+]?\.(inf|Inf|INF)$`)
	nanRegex       = regexp.MustCompile(`^\.(nan|NaN|NAN)$`)
	timestampRegex = regexp.MustCompile(`^\d{4}-\d{2}-\d{2}([Tt ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?)?$`)
	controlChars   = regexp.MustCompile("[\x00-\x08\x0b-\x1f\x7f]")
)

func looksLikeNumber(s string) bool {
	return floatRegex.MatchString(s) ||
		intRegex.MatchString(s) ||
		hexRegex.MatchString(s) ||
		octalRegex.MatchString(s) ||
		infRegex.MatchString(s) ||
		nanRegex.MatchString(s)
}

func looksLikeTimestamp(s string) bool {
	return timestampRegex.MatchString(s)
}

func needsQuoting(s string) bool {
	if len(s) == 0 {
		return true
	}
	if plainBoolNullSet[s] {
		return true
	}
	if looksLikeNumber(s) {
		return true
	}
	if looksLikeTimestamp(s) {
		return true
	}
	first := s[0]
	if yamlIndicators[first] {
		return true
	}
	if first == '-' && len(s) > 1 && s[1] == ' ' {
		return true
	}
	if first == ' ' || first == '\t' {
		return true
	}
	last := s[len(s)-1]
	if last == ' ' || last == '\t' {
		return true
	}
	if strings.Contains(s, ": ") {
		return true
	}
	if strings.Contains(s, " #") {
		return true
	}
	if strings.HasSuffix(s, ":") {
		return true
	}
	if controlChars.MatchString(s) {
		return true
	}
	return false
}

// quoteSingle emits PyYAML-style single-quoted scalar: doubles internal '.
func quoteSingle(s string) string {
	return "'" + strings.ReplaceAll(s, "'", "''") + "'"
}

// floatFields are PRML manifest fields whose value MUST round-trip as float
// even when integer-valued. PyYAML preserves float-ness through its native
// type system; JSON+Go must use the json.Number raw form to preserve "1.0".
var floatFields = map[string]bool{"threshold": true}

// renderNumber takes a json.Number (raw string) and the field name, returning
// the canonical byte representation. For float-typed fields, the output must
// match PyYAML's safe_dump float rendering exactly:
//
//   - integer-valued floats are rendered with at least one decimal place
//     (e.g. `1` → `1.0`)
//   - scientific-notation floats whose mantissa has no decimal place receive
//     a `.0` injection before the exponent (e.g. `1e-06` → `1.0e-06`),
//     matching Python's repr(float) which PyYAML inherits.
//
// JSON marshalled by Python's json.dumps already emits 2-digit zero-padded
// exponents (`1e-06`, not `1e-6`), so no exponent-padding is required for the
// v0.1 conformance vectors. Go's own encoding/json marshal does not pad,
// however, so any input round-tripped through Go's marshaler would fail; the
// canonicalizer expects raw json.Number strings preserved by UseNumber.
func renderNumber(n json.Number, field string) string {
	s := string(n)
	if !floatFields[field] {
		return s
	}
	eIdx := strings.IndexAny(s, "eE")
	if eIdx < 0 {
		// No exponent.
		if !strings.Contains(s, ".") {
			return s + ".0"
		}
		return s
	}
	// Has exponent: ensure mantissa has a decimal place.
	mantissa := s[:eIdx]
	exponent := s[eIdx:]
	if !strings.Contains(mantissa, ".") {
		return mantissa + ".0" + exponent
	}
	return s
}

// renderScalar emits the canonical form of a non-collection value.
// `field` is the parent key name (for hint-driven float rendering).
func renderScalar(v interface{}, field string) (string, error) {
	switch x := v.(type) {
	case nil:
		return "null", nil
	case bool:
		if x {
			return "true", nil
		}
		return "false", nil
	case json.Number:
		return renderNumber(x, field), nil
	case string:
		if needsQuoting(x) {
			return quoteSingle(x), nil
		}
		return x, nil
	default:
		return "", fmt.Errorf("renderScalar: unsupported type %T", v)
	}
}

// renderMapping emits a YAML block-style mapping with keys sorted
// lexicographically. Indent is the current depth in spaces.
// Returns the rendered text (without trailing newline at top level).
func renderMapping(m map[string]interface{}, indent int) (string, error) {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	pad := strings.Repeat(" ", indent)
	var lines []string
	for _, k := range keys {
		v := m[k]
		switch sub := v.(type) {
		case map[string]interface{}:
			lines = append(lines, fmt.Sprintf("%s%s:", pad, k))
			nested, err := renderMapping(sub, indent+2)
			if err != nil {
				return "", err
			}
			lines = append(lines, nested)
		case []interface{}:
			lines = append(lines, fmt.Sprintf("%s%s:", pad, k))
			for _, item := range sub {
				if itemMap, ok := item.(map[string]interface{}); ok {
					nested, err := renderMapping(itemMap, indent+2)
					if err != nil {
						return "", err
					}
					padNested := strings.Repeat(" ", indent+2)
					nestedLines := strings.Split(nested, "\n")
					nestedLines[0] = fmt.Sprintf("%s- %s", pad, strings.TrimPrefix(nestedLines[0], padNested))
					lines = append(lines, strings.Join(nestedLines, "\n"))
				} else {
					rendered, err := renderScalar(item, k)
					if err != nil {
						return "", err
					}
					lines = append(lines, fmt.Sprintf("%s- %s", pad, rendered))
				}
			}
		default:
			rendered, err := renderScalar(v, k)
			if err != nil {
				return "", err
			}
			lines = append(lines, fmt.Sprintf("%s%s: %s", pad, k, rendered))
		}
	}
	return strings.Join(lines, "\n"), nil
}

// Canonicalize emits the canonical byte sequence for a PRML manifest.
// The argument must be a map[string]interface{} as produced by
// json.Decoder with UseNumber enabled.
func Canonicalize(m map[string]interface{}) (string, error) {
	body, err := renderMapping(m, 0)
	if err != nil {
		return "", err
	}
	return body + "\n", nil
}

// ManifestHash computes the canonical SHA-256 of a manifest.
func ManifestHash(m map[string]interface{}) (string, error) {
	canonical, err := Canonicalize(m)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256([]byte(canonical))
	return hex.EncodeToString(sum[:]), nil
}

// ─────────────────────────────────────────────────────────────────────────
// Test-vector runner
// ─────────────────────────────────────────────────────────────────────────

type testVector struct {
	ID          string                 `json:"id"`
	Title       string                 `json:"title"`
	Description string                 `json:"description"`
	Input       map[string]interface{} `json:"input"`
	Canonical   string                 `json:"canonical"`
	Hash        string                 `json:"hash"`
}

func loadVectors(path string) ([]testVector, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read %s: %w", path, err)
	}
	dec := json.NewDecoder(strings.NewReader(string(data)))
	dec.UseNumber()
	var vectors []testVector
	if err := dec.Decode(&vectors); err != nil {
		return nil, fmt.Errorf("decode: %w", err)
	}
	return vectors, nil
}

// In test vectors, the `input` is parsed first as map[string]interface{}
// but with UseNumber so we get json.Number for numeric fields.
// Because UseNumber doesn't propagate through nested struct fields, we
// re-parse with a custom approach below.

func runVectors(path string) int {
	data, err := os.ReadFile(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "read %s: %v\n", path, err)
		return 11
	}
	// Parse the entire vectors JSON as []interface{} with UseNumber so
	// nested numeric fields preserve their raw JSON form.
	dec := json.NewDecoder(strings.NewReader(string(data)))
	dec.UseNumber()
	var raw []interface{}
	if err := dec.Decode(&raw); err != nil {
		fmt.Fprintf(os.Stderr, "decode: %v\n", err)
		return 11
	}
	pass, fail := 0, 0
	for _, vRaw := range raw {
		vec, ok := vRaw.(map[string]interface{})
		if !ok {
			fmt.Fprintln(os.Stderr, "vector is not an object")
			fail++
			continue
		}
		id, _ := vec["id"].(string)
		title, _ := vec["title"].(string)
		input, ok := vec["input"].(map[string]interface{})
		if !ok {
			fmt.Fprintf(os.Stderr, "vector %s: input is not an object\n", id)
			fail++
			continue
		}
		expectedCanonical, _ := vec["canonical"].(string)
		expectedHash, _ := vec["hash"].(string)

		produced, err := Canonicalize(input)
		if err != nil {
			fmt.Printf("FAIL  %s  %s  (canonicalize error: %v)\n", id, title, err)
			fail++
			continue
		}
		producedHash := computeSHA256(produced)
		if produced == expectedCanonical && producedHash == expectedHash {
			fmt.Printf("PASS  %s  %s\n", id, title)
			pass++
		} else {
			fmt.Printf("FAIL  %s  %s\n", id, title)
			diffPos := firstDiff(expectedCanonical, produced)
			if diffPos >= 0 {
				lo := max0(diffPos - 10)
				hiE := minN(len(expectedCanonical), diffPos+30)
				hiP := minN(len(produced), diffPos+30)
				fmt.Printf("        first diff @ char %d\n", diffPos)
				fmt.Printf("        expected: %q\n", expectedCanonical[lo:hiE])
				fmt.Printf("        produced: %q\n", produced[lo:hiP])
			}
			if producedHash != expectedHash {
				fmt.Printf("        expected hash: %s\n", expectedHash)
				fmt.Printf("        produced hash: %s\n", producedHash)
			}
			fail++
		}
	}
	fmt.Printf("\nResult: %d/%d vectors passed.\n", pass, pass+fail)
	if fail > 0 {
		return 10
	}
	return 0
}

func computeSHA256(s string) string {
	sum := sha256.Sum256([]byte(s))
	return hex.EncodeToString(sum[:])
}

func firstDiff(a, b string) int {
	n := len(a)
	if len(b) < n {
		n = len(b)
	}
	for i := 0; i < n; i++ {
		if a[i] != b[i] {
			return i
		}
	}
	if len(a) != len(b) {
		return n
	}
	return -1
}

func max0(x int) int {
	if x < 0 {
		return 0
	}
	return x
}

func minN(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// ─────────────────────────────────────────────────────────────────────────
// Verifier
// ─────────────────────────────────────────────────────────────────────────

const (
	exitPass     = 0
	exitTampered = 3
	exitFail     = 10
	exitGuard    = 11
)

func evaluatePredicate(observed, threshold float64, comparator string) (bool, error) {
	switch comparator {
	case ">=":
		return observed >= threshold, nil
	case "<=":
		return observed <= threshold, nil
	case ">":
		return observed > threshold, nil
	case "<":
		return observed < threshold, nil
	case "==":
		return observed == threshold, nil
	default:
		return false, fmt.Errorf("invalid comparator: %s", comparator)
	}
}

func cmdHash(specPath string) int {
	data, err := os.ReadFile(specPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "hash: %v\n", err)
		return exitGuard
	}
	dec := json.NewDecoder(strings.NewReader(string(data)))
	dec.UseNumber()
	var m map[string]interface{}
	if err := dec.Decode(&m); err != nil {
		fmt.Fprintf(os.Stderr, "hash: parse: %v\n", err)
		return exitGuard
	}
	h, err := ManifestHash(m)
	if err != nil {
		fmt.Fprintf(os.Stderr, "hash: %v\n", err)
		return exitGuard
	}
	fmt.Println(h)
	return exitPass
}

func cmdVerify(specPath, observedStr string) int {
	data, err := os.ReadFile(specPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "verify: %v\n", err)
		return exitGuard
	}
	dec := json.NewDecoder(strings.NewReader(string(data)))
	dec.UseNumber()
	var m map[string]interface{}
	if err := dec.Decode(&m); err != nil {
		fmt.Fprintf(os.Stderr, "verify: parse: %v\n", err)
		return exitGuard
	}
	canonical, err := Canonicalize(m)
	if err != nil {
		fmt.Fprintf(os.Stderr, "verify: %v\n", err)
		return exitGuard
	}
	computed := computeSHA256(canonical)
	sidecar := strings.TrimSuffix(specPath, getExt(specPath)) + ".prml.sha256"
	sidecarBytes, err := os.ReadFile(sidecar)
	if err != nil {
		fmt.Fprintf(os.Stderr, "verify: sidecar not found: %s\n", sidecar)
		return exitGuard
	}
	claimed := strings.TrimSpace(string(sidecarBytes))
	if computed != claimed {
		fmt.Println("TAMPERED")
		fmt.Printf("  recorded:    %s\n", claimed)
		fmt.Printf("  recomputed:  %s\n", computed)
		return exitTampered
	}
	if observedStr == "" {
		fmt.Printf("hash OK: %s\n", computed)
		fmt.Println("(no --observed value given; predicate not evaluated)")
		return exitPass
	}
	observed, err := strconv.ParseFloat(observedStr, 64)
	if err != nil {
		fmt.Fprintf(os.Stderr, "verify: --observed must be a finite number: %v\n", err)
		return exitGuard
	}
	comparator, _ := m["comparator"].(string)
	thresholdRaw, _ := m["threshold"].(json.Number)
	threshold, err := thresholdRaw.Float64()
	if err != nil {
		fmt.Fprintf(os.Stderr, "verify: threshold not numeric: %v\n", err)
		return exitGuard
	}
	metric, _ := m["metric"].(string)
	ok, err := evaluatePredicate(observed, threshold, comparator)
	if err != nil {
		fmt.Fprintf(os.Stderr, "verify: %v\n", err)
		return exitGuard
	}
	if ok {
		fmt.Printf("PASS  metric=%s  observed=%g  %s  threshold=%g\n",
			metric, observed, comparator, threshold)
		return exitPass
	}
	fmt.Printf("FAIL  metric=%s  observed=%g  NOT %s  threshold=%g\n",
		metric, observed, comparator, threshold)
	return exitFail
}

func getExt(p string) string {
	for i := len(p) - 1; i >= 0; i-- {
		if p[i] == '.' {
			return p[i:]
		}
		if p[i] == '/' {
			break
		}
	}
	return ""
}

// ─────────────────────────────────────────────────────────────────────────
// CLI
// ─────────────────────────────────────────────────────────────────────────

func usage() int {
	fmt.Fprintln(os.Stderr, `falsify-go — PRML v0.1 third reference implementation (Go)

Commands:
  test-vectors <vectors.json>            run conformance suite
  hash <spec.json>                       print canonical SHA-256
  verify <spec.json> [--observed <v>]    verify hash; if --observed, evaluate

Exit codes: 0=PASS, 3=TAMPERED, 10=FAIL, 11=GUARD
Spec:    https://spec.falsify.dev/v0.1`)
	return exitGuard
}

func main() {
	args := os.Args[1:]
	if len(args) == 0 {
		os.Exit(usage())
	}
	switch args[0] {
	case "test-vectors":
		if len(args) < 2 {
			os.Exit(usage())
		}
		os.Exit(runVectors(args[1]))
	case "hash":
		if len(args) < 2 {
			os.Exit(usage())
		}
		os.Exit(cmdHash(args[1]))
	case "verify":
		if len(args) < 2 {
			os.Exit(usage())
		}
		observed := ""
		for i, a := range args {
			if a == "--observed" && i+1 < len(args) {
				observed = args[i+1]
			}
		}
		os.Exit(cmdVerify(args[1], observed))
	case "-h", "--help":
		usage()
		os.Exit(0)
	default:
		os.Exit(usage())
	}
}

# Go (Golang) Interview Question Bank — Answers

### Sections 8, 9, and 10 (answered in original document order)

---

## 8. Coding Exercises — Strings, Arrays & Classic DSA in Go

### 8.1 Strings & basic manipulation

**144. Reverse a string (rune-safe)**

A naive `[]byte` reversal corrupts multi-byte UTF-8 characters. Convert to `[]rune` first.

```go
func reverseString(s string) string {
    r := []rune(s)
    for i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {
        r[i], r[j] = r[j], r[i]
    }
    return string(r)
}
```

**145. Palindrome check (with case/punctuation/space-insensitive variant)**

```go
func isPalindrome(s string) bool {
    r := []rune(s)
    for i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {
        if r[i] != r[j] {
            return false
        }
    }
    return true
}

func isPalindromeRelaxed(s string) bool {
    var clean []rune
    for _, r := range strings.ToLower(s) {
        if unicode.IsLetter(r) || unicode.IsDigit(r) {
            clean = append(clean, r)
        }
    }
    return isPalindrome(string(clean))
}
```

**146. Anagram check (frequency-count map)**

```go
func isAnagram(a, b string) bool {
    if len(a) != len(b) {
        return false
    }
    freq := make(map[rune]int)
    for _, r := range a {
        freq[r]++
    }
    for _, r := range b {
        freq[r]--
    }
    for _, c := range freq {
        if c != 0 {
            return false
        }
    }
    return true
}
```

**147. First non-repeating character**

```go
func firstNonRepeating(s string) rune {
    freq := make(map[rune]int)
    for _, r := range s {
        freq[r]++
    }
    for _, r := range s {
        if freq[r] == 1 {
            return r
        }
    }
    return -1 // sentinel: none found
}
```

**148. Character/word frequency count**

```go
func charFreq(s string) map[rune]int {
    freq := make(map[rune]int)
    for _, r := range s {
        freq[r]++
    }
    return freq
}

func wordFreq(s string) map[string]int {
    freq := make(map[string]int)
    for _, w := range strings.Fields(s) {
        freq[w]++
    }
    return freq
}
```

**149. Concurrent word-frequency count (chunked + merged)**

```go
func concurrentWordFreq(text string, numWorkers int) map[string]int {
    words := strings.Fields(text)
    chunkSize := (len(words) + numWorkers - 1) / numWorkers
    results := make(chan map[string]int, numWorkers)
    var wg sync.WaitGroup

    for i := 0; i < len(words); i += chunkSize {
        end := i + chunkSize
        if end > len(words) {
            end = len(words)
        }
        wg.Add(1)
        go func(chunk []string) {
            defer wg.Done()
            local := make(map[string]int)
            for _, w := range chunk {
                local[w]++
            }
            results <- local
        }(words[i:end])
    }

    go func() {
        wg.Wait()
        close(results)
    }()

    final := make(map[string]int)
    for partial := range results {
        for w, c := range partial {
            final[w] += c
        }
    }
    return final
}
```

Each goroutine owns its own local map (no shared-state contention), and merging happens single-threaded on the main goroutine after all partials arrive via the channel — this avoids needing a mutex entirely.

**150. Substring search from scratch (naive `strstr`)**

```go
func strStr(haystack, needle string) int {
    n, m := len(haystack), len(needle)
    if m == 0 {
        return 0
    }
    for i := 0; i+m <= n; i++ {
        if haystack[i:i+m] == needle {
            return i
        }
    }
    return -1
}
```

**151. Reverse words in a sentence in place**

```go
func reverseWords(s string) string {
    words := strings.Fields(s)
    for i, j := 0, len(words)-1; i < j; i, j = i+1, j-1 {
        words[i], words[j] = words[j], words[i]
    }
    return strings.Join(words, " ")
}
```

**152. Swap two variables without a temp variable**

```go
a, b := 1, 2
a, b = b, a // Go's multiple-assignment idiom
```

**153. Check if one string is a rotation of another**

A string `b` is a rotation of `a` if `len(a) == len(b)` and `b` is a substring of `a+a`.

```go
func isRotation(a, b string) bool {
    return len(a) == len(b) && strings.Contains(a+a, b)
}
```

**154. Longest substring without repeating characters (sliding window)**

```go
func longestUniqueSubstring(s string) int {
    lastSeen := make(map[byte]int)
    start, best := 0, 0
    for i := 0; i < len(s); i++ {
        if idx, ok := lastSeen[s[i]]; ok && idx >= start {
            start = idx + 1
        }
        lastSeen[s[i]] = i
        if i-start+1 > best {
            best = i - start + 1
        }
    }
    return best
}
```

**155. Run-length encoding/decoding**

```go
func rleEncode(s string) string {
    var b strings.Builder
    for i := 0; i < len(s); {
        j := i
        for j < len(s) && s[j] == s[i] {
            j++
        }
        b.WriteByte(s[i])
        b.WriteString(strconv.Itoa(j - i))
        i = j
    }
    return b.String()
}

func rleDecode(s string) string {
    var b strings.Builder
    i := 0
    for i < len(s) {
        ch := s[i]
        i++
        j := i
        for j < len(s) && s[j] >= '0' && s[j] <= '9' {
            j++
        }
        n, _ := strconv.Atoi(s[i:j])
        b.WriteString(strings.Repeat(string(ch), n))
        i = j
    }
    return b.String()
}
```

**156. Group anagrams**

```go
func groupAnagrams(strs []string) [][]string {
    groups := make(map[string][]string)
    for _, s := range strs {
        r := []rune(s)
        sort.Slice(r, func(i, j int) bool { return r[i] < r[j] })
        key := string(r)
        groups[key] = append(groups[key], s)
    }
    result := make([][]string, 0, len(groups))
    for _, v := range groups {
        result = append(result, v)
    }
    return result
}
```

---

### 8.2 Arrays, slices & two-pointer/sliding-window problems

**157. Two-sum (O(n²) and O(n) hashmap)**

```go
// O(n^2)
func twoSumBrute(nums []int, target int) [][2]int {
    var pairs [][2]int
    for i := 0; i < len(nums); i++ {
        for j := i + 1; j < len(nums); j++ {
            if nums[i]+nums[j] == target {
                pairs = append(pairs, [2]int{nums[i], nums[j]})
            }
        }
    }
    return pairs
}

// O(n) hashmap
func twoSum(nums []int, target int) (int, int, bool) {
    seen := make(map[int]int) // value -> index
    for i, n := range nums {
        if j, ok := seen[target-n]; ok {
            return j, i, true
        }
        seen[n] = i
    }
    return 0, 0, false
}
```

**158. Second largest element without sorting**

```go
func secondLargest(nums []int) (int, bool) {
    if len(nums) < 2 {
        return 0, false
    }
    first, second := math.MinInt64, math.MinInt64
    for _, n := range nums {
        if n > first {
            second = first
            first = n
        } else if n > second && n != first {
            second = n
        }
    }
    if second == math.MinInt64 {
        return 0, false
    }
    return second, true
}
```

**159. Missing number in 0..n**

Use Gauss's sum formula — `O(n)` time, `O(1)` space.

```go
func missingNumber(nums []int) int {
    n := len(nums)
    expected := n * (n + 1) / 2
    actual := 0
    for _, v := range nums {
        actual += v
    }
    return expected - actual
}
```

**160. Rotate a slice right by k steps, in place**

The reversal trick achieves this in O(n) time, O(1) extra space.

```go
func rotateRight(nums []int, k int) {
    n := len(nums)
    if n == 0 {
        return
    }
    k %= n
    reverse(nums)
    reverse(nums[:k])
    reverse(nums[k:])
}

func reverse(s []int) {
    for i, j := 0, len(s)-1; i < j; i, j = i+1, j-1 {
        s[i], s[j] = s[j], s[i]
    }
}
```

**161. Maximum subarray sum — Kadane's algorithm**

```go
func maxSubArray(nums []int) int {
    best, cur := nums[0], nums[0]
    for _, n := range nums[1:] {
        if cur < 0 {
            cur = n
        } else {
            cur += n
        }
        if cur > best {
            best = cur
        }
    }
    return best
}
```

Time complexity is O(n) — a single pass tracking the best running sum that resets whenever it goes negative, since a negative prefix can never help a future subarray.

**162. Merge two sorted slices without `sort.Sort`**

```go
func mergeSorted(a, b []int) []int {
    merged := make([]int, 0, len(a)+len(b))
    i, j := 0, 0
    for i < len(a) && j < len(b) {
        if a[i] <= b[j] {
            merged = append(merged, a[i])
            i++
        } else {
            merged = append(merged, b[j])
            j++
        }
    }
    merged = append(merged, a[i:]...)
    merged = append(merged, b[j:]...)
    return merged
}
```

**163. Intersection of two slices via map**

```go
func intersection(a, b []int) []int {
    set := make(map[int]bool, len(a))
    for _, v := range a {
        set[v] = true
    }
    var result []int
    seen := make(map[int]bool)
    for _, v := range b {
        if set[v] && !seen[v] {
            result = append(result, v)
            seen[v] = true
        }
    }
    return result
}
```

**164. Remove duplicates from a sorted slice in place**

```go
func removeDuplicates(nums []int) []int {
    if len(nums) == 0 {
        return nums
    }
    write := 1
    for read := 1; read < len(nums); read++ {
        if nums[read] != nums[write-1] {
            nums[write] = nums[read]
            write++
        }
    }
    return nums[:write]
}
```

**165. Generic `Filter` and `Reduce` using Go generics (1.18+)**

```go
func Filter[T any](s []T, pred func(T) bool) []T {
    result := make([]T, 0, len(s))
    for _, v := range s {
        if pred(v) {
            result = append(result, v)
        }
    }
    return result
}

func Reduce[T, U any](s []T, init U, f func(U, T) U) U {
    acc := init
    for _, v := range s {
        acc = f(acc, v)
    }
    return acc
}

// Example usage:
// evens := Filter([]int{1,2,3,4,5,6}, func(n int) bool { return n%2 == 0 })
// sum := Reduce([]int{1,2,3,4}, 0, func(acc, n int) int { return acc + n })
```

**166. 3Sum — triplets summing to zero**

Sort first, then use two pointers per fixed index, skipping duplicates — O(n²).

```go
func threeSum(nums []int) [][3]int {
    sort.Ints(nums)
    var result [][3]int
    for i := 0; i < len(nums)-2; i++ {
        if i > 0 && nums[i] == nums[i-1] {
            continue
        }
        l, r := i+1, len(nums)-1
        for l < r {
            sum := nums[i] + nums[l] + nums[r]
            switch {
            case sum < 0:
                l++
            case sum > 0:
                r--
            default:
                result = append(result, [3]int{nums[i], nums[l], nums[r]})
                for l < r && nums[l] == nums[l+1] {
                    l++
                }
                for l < r && nums[r] == nums[r-1] {
                    r--
                }
                l++
                r--
            }
        }
    }
    return result
}
```

**167. Maximum product of two integers in a slice**

Track the two largest and two smallest (to handle negative-number products).

```go
func maxProductOfTwo(nums []int) int {
    max1, max2 := math.MinInt64, math.MinInt64
    min1, min2 := math.MaxInt64, math.MaxInt64
    for _, n := range nums {
        if n > max1 {
            max2 = max1
            max1 = n
        } else if n > max2 {
            max2 = n
        }
        if n < min1 {
            min2 = min1
            min1 = n
        } else if n < min2 {
            min2 = n
        }
    }
    posProduct := max1 * max2
    negProduct := min1 * min2
    if negProduct > posProduct {
        return negProduct
    }
    return posProduct
}
```

**168. Binary search — iterative and recursive**

```go
func binarySearchIter(nums []int, target int) int {
    lo, hi := 0, len(nums)-1
    for lo <= hi {
        mid := lo + (hi-lo)/2
        switch {
        case nums[mid] == target:
            return mid
        case nums[mid] < target:
            lo = mid + 1
        default:
            hi = mid - 1
        }
    }
    return -1
}

func binarySearchRecursive(nums []int, target, lo, hi int) int {
    if lo > hi {
        return -1
    }
    mid := lo + (hi-lo)/2
    switch {
    case nums[mid] == target:
        return mid
    case nums[mid] < target:
        return binarySearchRecursive(nums, target, mid+1, hi)
    default:
        return binarySearchRecursive(nums, target, lo, mid-1)
    }
}
```

**169. Kth largest element — quickselect**

Average O(n), worst case O(n²); a heap-based approach gives a guaranteed O(n log k).

```go
func findKthLargest(nums []int, k int) int {
    target := len(nums) - k // index of kth largest in sorted-ascending order
    lo, hi := 0, len(nums)-1
    for {
        p := partition(nums, lo, hi)
        switch {
        case p == target:
            return nums[p]
        case p < target:
            lo = p + 1
        default:
            hi = p - 1
        }
    }
}

func partition(nums []int, lo, hi int) int {
    pivot := nums[hi]
    i := lo
    for j := lo; j < hi; j++ {
        if nums[j] < pivot {
            nums[i], nums[j] = nums[j], nums[i]
            i++
        }
    }
    nums[i], nums[hi] = nums[hi], nums[i]
    return i
}
```

---

### 8.3 Linked lists, trees, stacks & queues

```go
type ListNode struct {
    Val  int
    Next *ListNode
}
```

**170. Cycle detection — Floyd's tortoise and hare**

```go
func hasCycle(head *ListNode) bool {
    slow, fast := head, head
    for fast != nil && fast.Next != nil {
        slow = slow.Next
        fast = fast.Next.Next
        if slow == fast {
            return true
        }
    }
    return false
}
```

**171. Reverse a singly linked list**

```go
func reverseIterative(head *ListNode) *ListNode {
    var prev *ListNode
    for head != nil {
        next := head.Next
        head.Next = prev
        prev = head
        head = next
    }
    return prev
}

func reverseRecursive(head *ListNode) *ListNode {
    if head == nil || head.Next == nil {
        return head
    }
    newHead := reverseRecursive(head.Next)
    head.Next.Next = head
    head.Next = nil
    return newHead
}
```

**172. Merge two sorted linked lists**

```go
func mergeTwoLists(l1, l2 *ListNode) *ListNode {
    dummy := &ListNode{}
    cur := dummy
    for l1 != nil && l2 != nil {
        if l1.Val <= l2.Val {
            cur.Next = l1
            l1 = l1.Next
        } else {
            cur.Next = l2
            l2 = l2.Next
        }
        cur = cur.Next
    }
    if l1 != nil {
        cur.Next = l1
    } else {
        cur.Next = l2
    }
    return dummy.Next
}
```

**173. Find the middle node in one pass**

```go
func middleNode(head *ListNode) *ListNode {
    slow, fast := head, head
    for fast != nil && fast.Next != nil {
        slow = slow.Next
        fast = fast.Next.Next
    }
    return slow
}
```

**174. Stack and queue via slices (and the front-removal gotcha)**

```go
type Stack struct{ data []int }

func (s *Stack) Push(v int) { s.data = append(s.data, v) }
func (s *Stack) Pop() (int, bool) {
    if len(s.data) == 0 {
        return 0, false
    }
    v := s.data[len(s.data)-1]
    s.data = s.data[:len(s.data)-1]
    return v, true
}

type Queue struct{ data []int }

func (q *Queue) Enqueue(v int) { q.data = append(q.data, v) }
func (q *Queue) Dequeue() (int, bool) {
    if len(q.data) == 0 {
        return 0, false
    }
    v := q.data[0]
    q.data = q.data[1:] // O(n) — every remaining element shifts left
    return v, true
}
```

Removing from the front of a slice-backed queue (`s = s[1:]`) is O(n) because every remaining element's index shifts down — there's no true O(1) front-pop on a contiguous slice. For an efficient queue, use a ring buffer or `container/list` (doubly linked list) instead.

**175. Min stack — O(1) push/pop/min**

```go
type MinStack struct {
    data []int
    mins []int // mins[i] = minimum of data[0..i]
}

func (s *MinStack) Push(v int) {
    s.data = append(s.data, v)
    if len(s.mins) == 0 || v < s.mins[len(s.mins)-1] {
        s.mins = append(s.mins, v)
    } else {
        s.mins = append(s.mins, s.mins[len(s.mins)-1])
    }
}

func (s *MinStack) Pop() {
    s.data = s.data[:len(s.data)-1]
    s.mins = s.mins[:len(s.mins)-1]
}

func (s *MinStack) Min() int { return s.mins[len(s.mins)-1] }
```

**176. Balanced parentheses/brackets check**

```go
func isBalanced(s string) bool {
    pairs := map[rune]rune{')': '(', ']': '[', '}': '{'}
    var stack []rune
    for _, c := range s {
        switch c {
        case '(', '[', '{':
            stack = append(stack, c)
        case ')', ']', '}':
            if len(stack) == 0 || stack[len(stack)-1] != pairs[c] {
                return false
            }
            stack = stack[:len(stack)-1]
        }
    }
    return len(stack) == 0
}
```

**177. Binary search tree — Insert, Search, InOrder**

```go
type TreeNode struct {
    Val         int
    Left, Right *TreeNode
}

func (t *TreeNode) Insert(v int) *TreeNode {
    if t == nil {
        return &TreeNode{Val: v}
    }
    if v < t.Val {
        t.Left = t.Left.Insert(v)
    } else if v > t.Val {
        t.Right = t.Right.Insert(v)
    }
    return t
}

func (t *TreeNode) Search(v int) bool {
    if t == nil {
        return false
    }
    if v == t.Val {
        return true
    }
    if v < t.Val {
        return t.Left.Search(v)
    }
    return t.Right.Search(v)
}

func (t *TreeNode) InOrder(visit func(int)) {
    if t == nil {
        return
    }
    t.Left.InOrder(visit)
    visit(t.Val)
    t.Right.InOrder(visit)
}
```

**178. Validate a binary tree is a valid BST**

```go
func isValidBST(root *TreeNode) bool {
    return validate(root, nil, nil)
}

func validate(node *TreeNode, min, max *int) bool {
    if node == nil {
        return true
    }
    if min != nil && node.Val <= *min {
        return false
    }
    if max != nil && node.Val >= *max {
        return false
    }
    return validate(node.Left, min, &node.Val) && validate(node.Right, &node.Val, max)
}
```

**179. Maximum depth of a binary tree (recursive and BFS)**

```go
func maxDepthRecursive(root *TreeNode) int {
    if root == nil {
        return 0
    }
    l, r := maxDepthRecursive(root.Left), maxDepthRecursive(root.Right)
    if l > r {
        return l + 1
    }
    return r + 1
}

func maxDepthBFS(root *TreeNode) int {
    if root == nil {
        return 0
    }
    depth := 0
    queue := []*TreeNode{root}
    for len(queue) > 0 {
        depth++
        next := []*TreeNode{}
        for _, n := range queue {
            if n.Left != nil {
                next = append(next, n.Left)
            }
            if n.Right != nil {
                next = append(next, n.Right)
            }
        }
        queue = next
    }
    return depth
}
```

**180. Check if a binary tree is height-balanced**

```go
func isBalancedTree(root *TreeNode) bool {
    return checkHeight(root) != -1
}

func checkHeight(node *TreeNode) int {
    if node == nil {
        return 0
    }
    lh := checkHeight(node.Left)
    if lh == -1 {
        return -1
    }
    rh := checkHeight(node.Right)
    if rh == -1 {
        return -1
    }
    if abs(lh-rh) > 1 {
        return -1
    }
    if lh > rh {
        return lh + 1
    }
    return rh + 1
}

func abs(n int) int {
    if n < 0 {
        return -n
    }
    return n
}
```

**181. Level-order traversal (BFS) using a slice-backed queue**

```go
func levelOrder(root *TreeNode) [][]int {
    if root == nil {
        return nil
    }
    var result [][]int
    queue := []*TreeNode{root}
    for len(queue) > 0 {
        var level []int
        var next []*TreeNode
        for _, n := range queue {
            level = append(level, n.Val)
            if n.Left != nil {
                next = append(next, n.Left)
            }
            if n.Right != nil {
                next = append(next, n.Right)
            }
        }
        result = append(result, level)
        queue = next
    }
    return result
}
```

**182. Lowest common ancestor in a BST**

```go
func lowestCommonAncestor(root *TreeNode, p, q int) *TreeNode {
    node := root
    for node != nil {
        switch {
        case p < node.Val && q < node.Val:
            node = node.Left
        case p > node.Val && q > node.Val:
            node = node.Right
        default:
            return node
        }
    }
    return nil
}
```

**183. Serialize and deserialize a binary tree**

```go
func serialize(root *TreeNode) string {
    if root == nil {
        return "#"
    }
    return strconv.Itoa(root.Val) + "," + serialize(root.Left) + "," + serialize(root.Right)
}

func deserialize(data string) *TreeNode {
    tokens := strings.Split(data, ",")
    idx := 0
    var build func() *TreeNode
    build = func() *TreeNode {
        if tokens[idx] == "#" {
            idx++
            return nil
        }
        val, _ := strconv.Atoi(tokens[idx])
        idx++
        node := &TreeNode{Val: val}
        node.Left = build()
        node.Right = build()
        return node
    }
    return build()
}
```

---

### 8.4 Sorting, recursion & combinatorics

**184. Quicksort / mergesort from scratch**

```go
func quickSort(nums []int) {
    if len(nums) < 2 {
        return
    }
    pivot := nums[len(nums)/2]
    var less, equal, greater []int
    for _, n := range nums {
        switch {
        case n < pivot:
            less = append(less, n)
        case n == pivot:
            equal = append(equal, n)
        default:
            greater = append(greater, n)
        }
    }
    quickSort(less)
    quickSort(greater)
    copy(nums, append(append(less, equal...), greater...))
}

func mergeSort(nums []int) []int {
    if len(nums) < 2 {
        return nums
    }
    mid := len(nums) / 2
    left := mergeSort(nums[:mid])
    right := mergeSort(nums[mid:])
    return mergeSorted(left, right) // reuse the merge helper from Q162
}
```

**185. Print all permutations (recursive backtracking)**

```go
func permutations(s []rune) [][]rune {
    var result [][]rune
    var backtrack func(cur []rune, remaining []rune)
    backtrack = func(cur, remaining []rune) {
        if len(remaining) == 0 {
            perm := make([]rune, len(cur))
            copy(perm, cur)
            result = append(result, perm)
            return
        }
        for i := range remaining {
            next := append([]rune{}, remaining[:i]...)
            next = append(next, remaining[i+1:]...)
            backtrack(append(cur, remaining[i]), next)
        }
    }
    backtrack(nil, s)
    return result
}
```

**186. Print all subsets (power set)**

```go
func subsets(nums []int) [][]int {
    var result [][]int
    var backtrack func(start int, cur []int)
    backtrack = func(start int, cur []int) {
        subset := make([]int, len(cur))
        copy(subset, cur)
        result = append(result, subset)
        for i := start; i < len(nums); i++ {
            backtrack(i+1, append(cur, nums[i]))
        }
    }
    backtrack(0, nil)
    return result
}
```

**187. Recursive Fibonacci, then memoized**

```go
func fibNaive(n int) int {
    if n < 2 {
        return n
    }
    return fibNaive(n-1) + fibNaive(n-2)
}

func fibMemo(n int, memo map[int]int) int {
    if n < 2 {
        return n
    }
    if v, ok := memo[n]; ok {
        return v
    }
    result := fibMemo(n-1, memo) + fibMemo(n-2, memo)
    memo[n] = result
    return result
}
```

The naive version is O(2ⁿ) due to repeated subtree recomputation; memoization with a `map[int]int` cache cuts this to O(n).

**188. Min/max of a slice without third-party libraries**

```go
func minMax(nums []int) (min, max int) {
    min, max = nums[0], nums[0]
    for _, n := range nums[1:] {
        if n < min {
            min = n
        }
        if n > max {
            max = n
        }
    }
    return
}
```

**189. Check if slice is nil/empty; reverse in place**

```go
func isNilOrEmpty(s []int) bool {
    return len(s) == 0 // works for both nil and empty slices
}

func reverseInPlace(s []int) {
    for i, j := 0, len(s)-1; i < j; i, j = i+1, j-1 {
        s[i], s[j] = s[j], s[i]
    }
}
```

**190. Climbing stairs / coin change (basic DP, iterative)**

```go
// Climbing stairs: ways to reach step n taking 1 or 2 steps at a time
func climbStairs(n int) int {
    if n <= 2 {
        return n
    }
    prev2, prev1 := 1, 2
    for i := 3; i <= n; i++ {
        prev2, prev1 = prev1, prev1+prev2
    }
    return prev1
}

// Coin change: fewest coins to make amount (or -1 if impossible)
func coinChange(coins []int, amount int) int {
    dp := make([]int, amount+1)
    for i := 1; i <= amount; i++ {
        dp[i] = math.MaxInt32
        for _, c := range coins {
            if c <= i && dp[i-c]+1 < dp[i] {
                dp[i] = dp[i-c] + 1
            }
        }
    }
    if dp[amount] == math.MaxInt32 {
        return -1
    }
    return dp[amount]
}
```

**191. Basic trie (prefix tree) for autocomplete**

```go
type TrieNode struct {
    children map[rune]*TrieNode
    isEnd    bool
}

type Trie struct{ root *TrieNode }

func NewTrie() *Trie {
    return &Trie{root: &TrieNode{children: make(map[rune]*TrieNode)}}
}

func (t *Trie) Insert(word string) {
    node := t.root
    for _, c := range word {
        if node.children[c] == nil {
            node.children[c] = &TrieNode{children: make(map[rune]*TrieNode)}
        }
        node = node.children[c]
    }
    node.isEnd = true
}

func (t *Trie) StartsWith(prefix string) bool {
    node := t.root
    for _, c := range prefix {
        if node.children[c] == nil {
            return false
        }
        node = node.children[c]
    }
    return true
}
```

---

### 8.5 Concurrency + DSA combined

**192. Concurrent merge sort (goroutines + `sync.WaitGroup`)**

```go
func concurrentMergeSort(nums []int, depth int) []int {
    if len(nums) < 2 {
        return nums
    }
    if depth <= 0 {
        return mergeSort(nums) // fall back to sequential below a threshold
    }
    mid := len(nums) / 2
    var left, right []int
    var wg sync.WaitGroup
    wg.Add(2)
    go func() {
        defer wg.Done()
        left = concurrentMergeSort(nums[:mid], depth-1)
    }()
    go func() {
        defer wg.Done()
        right = concurrentMergeSort(nums[mid:], depth-1)
    }()
    wg.Wait()
    return mergeSorted(left, right)
}
```

A `depth` (or size) cutoff caps how deep we keep spawning goroutines — unbounded goroutine creation on tiny subarrays adds scheduling overhead that outweighs the parallelism gained.

**193. `SumOfSquares(c int)` — for-select streaming with cancellation**

```go
func SumOfSquares(c int) (<-chan int, chan<- struct{}) {
    out := make(chan int)
    quit := make(chan struct{})
    go func() {
        defer close(out)
        for i := 1; i <= c; i++ {
            select {
            case out <- i * i:
            case <-quit:
                return
            }
        }
    }()
    return out, quit
}
```

**194. Sum of a slice via N goroutines, combined safely**

```go
func concurrentSum(nums []int, n int) int {
    chunkSize := (len(nums) + n - 1) / n
    var wg sync.WaitGroup
    var mu sync.Mutex
    total := 0

    for i := 0; i < len(nums); i += chunkSize {
        end := i + chunkSize
        if end > len(nums) {
            end = len(nums)
        }
        wg.Add(1)
        go func(part []int) {
            defer wg.Done()
            partial := 0
            for _, v := range part {
                partial += v
            }
            mu.Lock()
            total += partial
            mu.Unlock()
        }(nums[i:end])
    }
    wg.Wait()
    return total
}
```

**195. Concurrent binary tree traversal, merged through a channel**

```go
func concurrentSumTree(root *TreeNode) int {
    results := make(chan int)
    var wg sync.WaitGroup

    var walk func(n *TreeNode)
    walk = func(n *TreeNode) {
        defer wg.Done()
        if n == nil {
            return
        }
        results <- n.Val
        if n.Left != nil {
            wg.Add(1)
            go walk(n.Left)
        }
        if n.Right != nil {
            wg.Add(1)
            go walk(n.Right)
        }
    }

    wg.Add(1)
    go walk(root)

    go func() {
        wg.Wait()
        close(results)
    }()

    sum := 0
    for v := range results {
        sum += v
    }
    return sum
}
```

**196. Thread-safe HTTP counter**

```go
type Counter struct {
    mu    sync.Mutex
    count int64
}

func (c *Counter) Handler(w http.ResponseWriter, r *http.Request) {
    c.mu.Lock()
    c.count++
    current := c.count
    c.mu.Unlock()
    fmt.Fprintf(w, "count: %d\n", current)
}

// atomic alternative — avoids the mutex entirely:
type AtomicCounter struct{ count int64 }

func (c *AtomicCounter) Handler(w http.ResponseWriter, r *http.Request) {
    current := atomic.AddInt64(&c.count, 1)
    fmt.Fprintf(w, "count: %d\n", current)
}
```

`sync/atomic` is preferable here since the critical section is a single integer increment — it avoids lock/unlock overhead entirely.

**197. Generic order-preserving dedup, parallelized across chunks**

```go
func Dedup[T comparable](s []T) []T {
    seen := make(map[T]bool, len(s))
    result := make([]T, 0, len(s))
    for _, v := range s {
        if !seen[v] {
            seen[v] = true
            result = append(result, v)
        }
    }
    return result
}

// Parallel: dedup each chunk independently, then dedup the concatenation
// (preserves order since chunks are processed in original sequence).
func ParallelDedup[T comparable](s []T, numChunks int) []T {
    chunkSize := (len(s) + numChunks - 1) / numChunks
    partials := make([][]T, numChunks)
    var wg sync.WaitGroup

    for i := 0; i < numChunks; i++ {
        start := i * chunkSize
        end := start + chunkSize
        if start >= len(s) {
            break
        }
        if end > len(s) {
            end = len(s)
        }
        wg.Add(1)
        go func(idx int, chunk []T) {
            defer wg.Done()
            partials[idx] = Dedup(chunk)
        }(i, s[start:end])
    }
    wg.Wait()

    var combined []T
    for _, p := range partials {
        combined = append(combined, p...)
    }
    return Dedup(combined)
}
```

**198. In-memory key-value store with TTL expiration**

```go
type entry struct {
    value      string
    expiresAt  time.Time
}

type KVStore struct {
    mu   sync.Mutex
    data map[string]entry
}

func NewKVStore(sweepInterval time.Duration) *KVStore {
    kv := &KVStore{data: make(map[string]entry)}
    go kv.sweep(sweepInterval)
    return kv
}

func (kv *KVStore) Set(key, value string, ttl time.Duration) {
    kv.mu.Lock()
    defer kv.mu.Unlock()
    kv.data[key] = entry{value: value, expiresAt: time.Now().Add(ttl)}
}

func (kv *KVStore) Get(key string) (string, bool) {
    kv.mu.Lock()
    defer kv.mu.Unlock()
    e, ok := kv.data[key]
    if !ok || time.Now().After(e.expiresAt) {
        return "", false
    }
    return e.value, true
}

func (kv *KVStore) sweep(interval time.Duration) {
    ticker := time.NewTicker(interval)
    defer ticker.Stop()
    for range ticker.C {
        kv.mu.Lock()
        now := time.Now()
        for k, e := range kv.data {
            if now.After(e.expiresAt) {
                delete(kv.data, k)
            }
        }
        kv.mu.Unlock()
    }
}
```

**199. Concurrent-safe LRU cache (map + doubly linked list + mutex)**

```go
type LRUNode struct {
    key, value int
    prev, next *LRUNode
}

type LRUCache struct {
    mu       sync.Mutex
    capacity int
    cache    map[int]*LRUNode
    head, tail *LRUNode // head = most recently used, tail = least
}

func NewLRUCache(capacity int) *LRUCache {
    head, tail := &LRUNode{}, &LRUNode{}
    head.next, tail.prev = tail, head
    return &LRUCache{capacity: capacity, cache: make(map[int]*LRUNode), head: head, tail: tail}
}

func (c *LRUCache) remove(n *LRUNode) {
    n.prev.next, n.next.prev = n.next, n.prev
}

func (c *LRUCache) insertAtHead(n *LRUNode) {
    n.next, n.prev = c.head.next, c.head
    c.head.next.prev, c.head.next = n, n
}

func (c *LRUCache) Get(key int) (int, bool) {
    c.mu.Lock()
    defer c.mu.Unlock()
    n, ok := c.cache[key]
    if !ok {
        return 0, false
    }
    c.remove(n)
    c.insertAtHead(n)
    return n.value, true
}

func (c *LRUCache) Put(key, value int) {
    c.mu.Lock()
    defer c.mu.Unlock()
    if n, ok := c.cache[key]; ok {
        n.value = value
        c.remove(n)
        c.insertAtHead(n)
        return
    }
    if len(c.cache) >= c.capacity {
        lru := c.tail.prev
        c.remove(lru)
        delete(c.cache, lru.key)
    }
    n := &LRUNode{key: key, value: value}
    c.cache[key] = n
    c.insertAtHead(n)
}
```

The map gives O(1) lookup; the doubly linked list gives O(1) reordering and eviction. The mutex serializes both structures together so they never drift out of sync under concurrent access.

**200. A simplified `sync.WaitGroup` using channels**

```go
type MyWaitGroup struct {
    counter chan struct{}
    done    chan struct{}
    mu      sync.Mutex
    n       int
}

func NewMyWaitGroup() *MyWaitGroup {
    return &MyWaitGroup{done: make(chan struct{})}
}

func (wg *MyWaitGroup) Add(delta int) {
    wg.mu.Lock()
    wg.n += delta
    wg.mu.Unlock()
}

func (wg *MyWaitGroup) Done() {
    wg.mu.Lock()
    wg.n--
    remaining := wg.n
    wg.mu.Unlock()
    if remaining == 0 {
        close(wg.done)
    }
}

func (wg *MyWaitGroup) Wait() {
    <-wg.done
}
```

This is a simplified single-use version (real `sync.WaitGroup` supports reuse after the counter returns to zero, which requires more careful generation tracking) — but it demonstrates the core idea: `Done()` closing a channel is what lets `Wait()` unblock, since a closed channel receive never blocks.

**201. Concurrent fetch with a max-concurrency semaphore**

```go
type FetchResult struct {
    URL   string
    Body  string
    Err   error
}

func fetchAllConcurrently(urls []string, maxConcurrency int) []FetchResult {
    sem := make(chan struct{}, maxConcurrency)
    results := make([]FetchResult, len(urls))
    var wg sync.WaitGroup

    for i, url := range urls {
        wg.Add(1)
        go func(idx int, u string) {
            defer wg.Done()
            sem <- struct{}{}        // acquire
            defer func() { <-sem }() // release

            resp, err := http.Get(u)
            if err != nil {
                results[idx] = FetchResult{URL: u, Err: err}
                return
            }
            defer resp.Body.Close()
            body, err := io.ReadAll(resp.Body)
            results[idx] = FetchResult{URL: u, Body: string(body), Err: err}
        }(i, url)
    }
    wg.Wait()
    return results
}
```

Each goroutine writes to its own pre-allocated index in `results`, so there's no shared-write contention despite running concurrently; errors are captured per-result instead of aborting the batch.

**202. Flatten a nested `[]interface{}` recursively**

```go
func flatten(nested []interface{}) []interface{} {
    var result []interface{}
    for _, v := range nested {
        if inner, ok := v.([]interface{}); ok {
            result = append(result, flatten(inner)...)
        } else {
            result = append(result, v)
        }
    }
    return result
}
```

---

## 9. System-Design-Adjacent Go Questions

**203. Designing a Go service for 10,000 concurrent connections**

Go's goroutine model is the key enabler here. Goroutines start at roughly 2–8 KB of stack (growing dynamically as needed), versus the typically 1–8 MB fixed stack of an OS thread, so 10,000 goroutines cost a few tens of megabytes rather than gigabytes. The Go runtime multiplexes goroutines onto a small pool of OS threads (the M:N scheduler, GOMAXPROCS-bound), and network I/O is handled by an integrated netpoller (epoll/kqueue/IOCP under the hood) so a goroutine blocked on a read or write doesn't block an OS thread — it's parked and the thread is freed to run other goroutines. In practice: use `net/http`'s default one-goroutine-per-connection model (it already scales this way out of the box), set sane `ReadTimeout`/`WriteTimeout`/`IdleTimeout` on the server to avoid resource exhaustion from slow or stalled clients, use connection pooling for any downstream calls (DB, Redis), and consider a worker-pool or semaphore pattern if per-request work is CPU-heavy rather than I/O-bound, since CPU-bound work doesn't benefit from goroutine multiplexing the same way I/O-bound work does. This contrasts with thread-per-connection models in languages like Java (pre-virtual-threads) or C, where each connection costs a full OS thread and the system hits scheduler and memory limits far sooner.

**204. Database connection pooling with `database/sql`**

`database/sql` has a built-in connection pool — you don't manage raw connections yourself. Key knobs: `SetMaxOpenConns(n)` caps the total number of open connections (in-use + idle) to avoid overwhelming the database; `SetMaxIdleConns(n)` controls how many idle connections are kept warm for reuse, reducing the cost of repeated handshake/auth on bursty traffic; `SetConnMaxLifetime(d)` forces connections to be recycled periodically, which helps with load balancers, DNS changes, and stale connections behind proxies; `SetConnMaxIdleTime(d)` closes connections that have sat idle too long. A common production starting point is to set `MaxOpenConns` based on the database's own connection limit divided across service instances, and `MaxIdleConns` close to (or equal to) `MaxOpenConns` to avoid needless connection churn under steady load.

**205. Retries with exponential backoff, respecting context cancellation**

```go
func retryWithBackoff(ctx context.Context, maxAttempts int, fn func() error) error {
    var err error
    backoff := 100 * time.Millisecond
    for attempt := 0; attempt < maxAttempts; attempt++ {
        if err = fn(); err == nil {
            return nil
        }
        select {
        case <-ctx.Done():
            return ctx.Err()
        case <-time.After(backoff):
            backoff *= 2
        }
    }
    return err
}
```

The `select` between `ctx.Done()` and the backoff timer is the critical piece — without it, a retry loop keeps sleeping and retrying even after the caller has given up (e.g., the original HTTP request was cancelled), wasting resources and potentially returning a stale response. Adding jitter (`backoff + rand.Int63n(jitterRange)`) is also common in production to avoid synchronized retry storms ("thundering herd") across many clients.

**206. Circuit breaker pattern for a flaky downstream service**

A circuit breaker tracks failure rate and moves between three states: closed (calls pass through normally), open (calls fail fast without hitting the downstream service, after too many recent failures), and half-open (after a cooldown, a limited number of trial calls are allowed through to test if the dependency has recovered). A minimal sketch:

```go
type CircuitBreaker struct {
    mu           sync.Mutex
    failures     int
    threshold    int
    state        string // "closed", "open", "half-open"
    lastFailure  time.Time
    cooldown     time.Duration
}

func (cb *CircuitBreaker) Call(fn func() error) error {
    cb.mu.Lock()
    if cb.state == "open" {
        if time.Since(cb.lastFailure) > cb.cooldown {
            cb.state = "half-open"
        } else {
            cb.mu.Unlock()
            return errors.New("circuit open: failing fast")
        }
    }
    cb.mu.Unlock()

    err := fn()

    cb.mu.Lock()
    defer cb.mu.Unlock()
    if err != nil {
        cb.failures++
        cb.lastFailure = time.Now()
        if cb.failures >= cb.threshold {
            cb.state = "open"
        }
        return err
    }
    cb.failures = 0
    cb.state = "closed"
    return nil
}
```

In production, reach for a maintained library (e.g. `sony/gobreaker`) rather than hand-rolling this, but understanding the state machine is what interviewers are testing.

**207. Structuring for graceful degradation when a dependency is unavailable**

The core idea is treating the dependency as optional in the request path rather than a hard blocker. Practical patterns: define an interface for the dependency (e.g., a `Cache` interface around Redis) so a no-op or in-memory fallback can be swapped in; wrap calls with timeouts via `context.WithTimeout` so a hung Redis doesn't hang the whole request; use the circuit breaker pattern above so repeated failures stop being retried and instead fail fast, falling back to a default (e.g., skip the cache and hit the database directly, or serve slightly stale data); and emit metrics/logs when running in degraded mode so on-call engineers know the dependency is down without the service itself going down. The general principle: a "nice-to-have" dependency failing should degrade functionality (e.g., slower responses, no caching) rather than cause an outage.

**208. Batching and debouncing writes with a buffered channel + worker**

```go
type WriteBatcher struct {
    buf      chan Record
    maxSize  int
    maxDelay time.Duration
    flush    func([]Record)
}

func (b *WriteBatcher) Run() {
    batch := make([]Record, 0, b.maxSize)
    timer := time.NewTimer(b.maxDelay)
    defer timer.Stop()

    flushNow := func() {
        if len(batch) > 0 {
            b.flush(batch)
            batch = make([]Record, 0, b.maxSize)
        }
        timer.Reset(b.maxDelay)
    }

    for {
        select {
        case rec, ok := <-b.buf:
            if !ok {
                flushNow()
                return
            }
            batch = append(batch, rec)
            if len(batch) >= b.maxSize {
                flushNow()
            }
        case <-timer.C:
            flushNow()
        }
    }
}
```

This flushes whichever threshold is hit first — size (`maxSize` records buffered) or time (`maxDelay` elapsed since the last flush) — which is the standard size-or-time debounce pattern for batching high-throughput writes without unbounded latency.

**209. Rate limiter design — token bucket / leaky bucket per client**

The token bucket is the more common choice for API gateways since it allows bursts up to the bucket size while enforcing a steady-state rate. Using the standard library's `golang.org/x/time/rate`:

```go
type ClientLimiter struct {
    mu       sync.Mutex
    limiters map[string]*rate.Limiter
    r        rate.Limit
    burst    int
}

func (cl *ClientLimiter) getLimiter(clientID string) *rate.Limiter {
    cl.mu.Lock()
    defer cl.mu.Unlock()
    l, ok := cl.limiters[clientID]
    if !ok {
        l = rate.NewLimiter(cl.r, cl.burst)
        cl.limiters[clientID] = l
    }
    return l
}

func (cl *ClientLimiter) Allow(clientID string) bool {
    return cl.getLimiter(clientID).Allow()
}
```

For a hand-rolled version (common as a "build it yourself" follow-up), a goroutine with a `time.Ticker` refills tokens into a per-client counter at a fixed rate, and `Allow()` does an atomic decrement-if-positive check. At scale across multiple gateway instances, per-client state needs to live in a shared store (Redis with `INCR`+`EXPIRE`, or a Lua script for atomicity) rather than in-process maps, since in-process limiters only enforce the limit per instance, not globally.

**210. Distributed tracing / context propagation in Go**

`context.Context` is the propagation vehicle within a single process — it carries a request-scoped span and metadata (trace ID, span ID, baggage) through function calls, including across goroutine boundaries spawned for a single request. OpenTelemetry's Go SDK hooks into this: a span is started at the entry point (e.g., an HTTP middleware wraps `otelhttp.NewHandler`), stored in the `context.Context`, and child spans for downstream calls (DB queries, outbound HTTP, RPC) are created from that context so they nest correctly in the trace. Cross-service propagation happens via headers — typically the W3C `traceparent` header — injected into outbound requests and extracted from inbound ones by the OpenTelemetry propagator, so a trace ID stays consistent as a request hops between services. The key discipline interviewers look for: always pass `context.Context` as the first parameter through call chains (idiomatic Go), never store it in a struct field, and never start a "detached" goroutine for request-scoped work without deriving its context from the parent (or you lose cancellation propagation and tracing continuity).

---

## 10. "Tricky / Gotcha" Quick-Fire Round

**211. `defer` LIFO order**

```go
func main() {
    defer fmt.Println("1")
    defer fmt.Println("2")
    defer fmt.Println("3")
}
```

Output:

```
3
2
1
```

Deferred calls are pushed onto a stack and run in last-in-first-out order when the surrounding function returns — the last `defer` registered runs first.

**212 (Section 10). Why pre-1.22 loops print `5 5 5 5 5`, and how 1.22 fixed it**

```go
for i := 0; i < 5; i++ {
    go func() { fmt.Println(i) }()
}
```

Before Go 1.22, `i` was a single variable shared across all loop iterations — the closures captured a reference to that one variable, not a snapshot of its value at each iteration. By the time the goroutines actually ran (after the loop finished), `i` had already reached 5, so all five goroutines printed the same final value (in practice often `5 5 5 5 5`, though scheduling could interleave differently). The classic pre-1.22 fix was to shadow the variable per iteration: `i := i` inside the loop body, or pass it as a parameter: `go func(i int) { fmt.Println(i) }(i)`. Go 1.22 changed the language semantics so that `for` loop variables (both classic `for i :=` loops and `for range`) are now scoped per-iteration by default — each iteration gets its own fresh copy of the variable — eliminating this entire class of bug without requiring any code change.

**213. Returning a pointer to a local variable**

This is safe in Go, unlike C. The Go compiler performs escape analysis: if it determines a local variable's address outlives the function (e.g., it's returned, or captured by a closure, or stored somewhere that escapes), the compiler allocates that variable on the heap instead of the stack, and the garbage collector keeps it alive as long as something references it. So `func foo() *int { x := 5; return &x }` is perfectly safe — `x` escapes to the heap automatically. (You can inspect this with `go build -gcflags="-m"`.)

**214. Why structs compare with `==` but slices don't**

A struct is `==`-comparable if every one of its fields is itself comparable (so structs of ints, strings, arrays, bools, etc. compare fine; a struct containing a slice, map, or function field is not comparable). Slices, maps, and functions are explicitly excluded from `==` comparison in the language spec because there's no well-defined notion of equality for them: two slices could share a backing array, partially overlap, or have different capacities while holding identical elements — there's no single obvious semantic the compiler can pick. The only valid slice comparison is against `nil` (`s == nil`); for content equality you must use `reflect.DeepEqual` or write an explicit element-by-element comparison (`slices.Equal` in Go 1.21+).

**215. Calling a pointer-receiver method on a nil pointer**

This is not always a panic. A pointer-receiver method can be called on a nil pointer just fine, as long as the method body doesn't dereference the nil receiver. For example, a method that just checks `if t == nil { return defaultValue }` works perfectly on a nil `*T`. It only panics the moment the method body tries to actually access a field or call something through the nil pointer (`t.field` on a nil `t`). This pattern is actually used deliberately in Go for things like nil-safe linked-list or tree methods.

**216. `interface{}` holding a nil `*MyStruct` is not itself `nil`**

This is the classic "nil interface vs. nil pointer" gotcha. An interface value internally is a `(type, value)` pair. If you assign a nil `*MyStruct` to an `interface{}` (or `error`), the interface's type field gets set to `*MyStruct` and the value field is nil — but the interface itself is not nil, because it does have a concrete type attached. So `var p *MyStruct = nil; var i interface{} = p; i == nil` evaluates to `false`. This commonly bites people when a function declares a named return of type `error`, sets a typed nil pointer error variable, and returns it — the caller's `if err != nil` check then unexpectedly evaluates true even though "logically" there was no error. The fix is to return a bare untyped `nil` literal directly rather than a typed nil variable when no error occurred.

**217. `range` loop variable mutation: value copy vs. mutating via index, and the Go 1.22 change**

```go
type Item struct{ Name string }
items := []Item{{"a"}, {"b"}, {"c"}}

// Mutating the loop variable does NOT mutate the underlying slice —
// v is a copy of each element.
for _, v := range items {
    v.Name = "x" // no-op as far as items is concerned
}

// Mutating via index DOES mutate the underlying slice.
for i := range items {
    items[i].Name = "x" // this actually changes items
}
```

Separately, in goroutine-capture scenarios pre-1.22, `for _, v := range items { go func(){ fmt.Println(v) }() }` had the same shared-variable bug as the indexed loop in Q166 — all goroutines could observe the same final `v`. Go 1.22's per-iteration variable scoping fixes that specific class of bug (each iteration's `v` is now distinct), but it does not change the value-copy-vs-index semantics shown above — `range`-ing over a slice of structs still gives you a copy per iteration; that's a separate, unrelated property of `range`.

**218. Appending can silently corrupt an unrelated slice**

This happens when two slices share the same underlying backing array. If slice `a` has spare capacity (`len(a) < cap(a)`) and you `append()` to it without exceeding that capacity, Go writes the new element directly into the existing backing array rather than allocating a new one. If another slice `b` was created by sub-slicing the same array and happens to overlap that region (e.g., `b := original[2:4]` while `a := original[0:2]` still has capacity reaching into index 2), appending to `a` silently overwrites what `b` sees at that index — with no error, since both slices are simply different windows onto the same memory. The safe fix is to use a full slice expression (`s[:len(s):cap(s)]`) to cap a slice's capacity exactly at its length when handing it off, forcing any future `append` on it to allocate a fresh array instead of clobbering shared memory.

**219. Why unbuffered channel sends block until both sides are ready**

An unbuffered channel has zero internal storage capacity — it's a pure synchronization point (a "rendezvous"), not a queue. A send on an unbuffered channel only completes once a receiver is simultaneously ready to take the value; until then, the sending goroutine blocks. Symmetrically, a receive blocks until a sender is ready. This gives unbuffered channels a strong happens-before guarantee: the send completes strictly after the corresponding receive has started, which is useful for handoff-style synchronization (e.g., "wait until the worker has picked this up"). A buffered channel, by contrast, has internal capacity `N` — a send only blocks once the buffer is full (no receiver needs to be ready yet, as long as there's room), and a receive only blocks once the buffer is empty. This makes buffered channels behave more like an async queue with backpressure that only kicks in once the buffer fills, whereas unbuffered channels enforce synchronous, lockstep coordination between exactly one sender and one receiver per value.

---

_End of Sections 8–10 answers._

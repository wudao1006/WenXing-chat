def quicksort(nums, k, left, right):
    i, j = left, right
    while i < j:
        while i < j and nums[j] >= nums[left]:
            j -= 1
        while i < j and nums[i] <= nums[left]:
            i += 1
        print(i, j)
        t = nums[i]
        nums[i] = nums[j]
        nums[j] = t
    print(i, j)
    t = nums[i]
    nums[i] = nums[left]
    nums[left] = t
    if i < k:
        return quicksort(nums, k, i + 1, right)
    elif i > k:
        return quicksort(nums, k, left, i - 1)
    return nums[k]


def findKthLargest(nums, k):
    """
        :type nums: List[int]
        :type k: int
        :rtype: int
        """
    n = len(nums)
    return quicksort(nums, n-k, 0, n - 1)


nums = [2,1]
k = 1

if 3 in nums:
    print(True)
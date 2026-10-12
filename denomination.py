
def calculate_notes(amount, inventory):
    """
    Find an exact combination of available ATM notes.
    Returns {denomination: count}, or None if impossible.
    """
    if amount <= 0 or amount % 50 != 0:
        return None

    # Keep only usable denominations and available notes.
    notes = [
        (int(denomination), int(count))
        for denomination, count in inventory
        if int(denomination) > 0 and int(count) > 0
    ]

    # Dynamic programming: find a valid exact combination.
    # dp[sum] stores the notes used to make that sum.
    dp = {0: {}}

    for denomination, available in notes:
        previous_sums = list(dp.keys())

        for current_sum in previous_sums:
            for count in range(
                1,
                min(available, (amount - current_sum) // denomination) + 1
            ):
                new_sum = current_sum + denomination * count

                if new_sum <= amount and new_sum not in dp:
                    combination = dp[current_sum].copy()
                    combination[denomination] = count
                    dp[new_sum] = combination

                if amount in dp:
                    return dp[amount]

    return dp.get(amount)

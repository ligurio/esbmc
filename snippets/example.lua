local function factorial(n)
    if n == 0 or n == 1 then
        return 1
    else
        return n * factorial(n - 1)
    end
end

local n = nondet_int()
__ESBMC_assume(n > 0);
__ESBMC_assume(n < 6);

local result = factorial(n)
assert(result ~= 120)

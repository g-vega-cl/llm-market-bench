export interface DiffChange {
    value: string;
    added?: boolean;
    removed?: boolean;
}

/**
 * Builds the Longest Common Subsequence (LCS) matrix.
 */
function buildLcsMatrix(oldLines: string[], newLines: string[]): number[][] {
    const m = oldLines.length;
    const n = newLines.length;
    const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));

    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            if (oldLines[i - 1] === newLines[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }
    return dp;
}

/**
 * Backtracks through the LCS matrix to determine line differences.
 */
function backtrackLcs(oldLines: string[], newLines: string[], dp: number[][]): DiffChange[] {
    const result: DiffChange[] = [];
    let i = oldLines.length;
    let j = newLines.length;

    while (i > 0 || j > 0) {
        if (i > 0 && j > 0 && oldLines[i - 1] === newLines[j - 1]) {
            result.unshift({ value: oldLines[i - 1] });
            i--;
            j--;
        } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
            result.unshift({ value: newLines[j - 1], added: true });
            j--;
        } else {
            result.unshift({ value: oldLines[i - 1], removed: true });
            i--;
        }
    }
    return result;
}

/**
 * Perform a line-by-line diff using a custom Longest Common Subsequence (LCS) algorithm.
 * Returns a list of DiffChange items representing unchanged, added, or removed lines.
 */
export function diffLines(oldStr: string, newStr: string): DiffChange[] {
    const oldLines = oldStr ? oldStr.split('\n') : [];
    const newLines = newStr ? newStr.split('\n') : [];
    const dp = buildLcsMatrix(oldLines, newLines);
    return backtrackLcs(oldLines, newLines, dp);
}

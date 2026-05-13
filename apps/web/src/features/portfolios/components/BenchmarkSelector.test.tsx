import { fireEvent, render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { BENCHMARK_OPTIONS, BenchmarkSelector } from './BenchmarkSelector';

test('renders BenchmarkSelector with all benchmark options', () => {
    render(<BenchmarkSelector selected="" onChange={vi.fn()} />);

    expect(screen.getByLabelText(/Benchmark/i)).toBeInTheDocument();

    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();

    BENCHMARK_OPTIONS.forEach((opt) => {
        expect(screen.getByText(new RegExp(`${opt.label}`))).toBeInTheDocument();
    });
});

test('calls onChange when a benchmark is selected', () => {
    const handleChange = vi.fn();
    render(<BenchmarkSelector selected="" onChange={handleChange} />);

    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'SPY' } });

    expect(handleChange).toHaveBeenCalledWith('SPY');
});

test('displays the selected benchmark value', () => {
    render(<BenchmarkSelector selected="QQQ" onChange={vi.fn()} />);

    const select = screen.getByRole('combobox') as HTMLSelectElement;
    expect(select.value).toBe('QQQ');
});

test('shows "None" option when no benchmark is selected', () => {
    render(<BenchmarkSelector selected="" onChange={vi.fn()} />);

    expect(screen.getByText(/None/i)).toBeInTheDocument();
});

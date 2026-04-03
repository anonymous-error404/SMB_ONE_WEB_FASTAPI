import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format number to Indian currency format with lakhs and crores
 * @param amount - The amount to format
 * @param showSymbol - Whether to show ₹ symbol (default: true)
 * @returns Formatted string like ₹1,50,000 or ₹1.5L or ₹1.5Cr
 */
export function formatIndianCurrency(amount: number, showSymbol: boolean = true): string {
  const symbol = showSymbol ? '₹' : '';
  const absAmount = Math.abs(amount);
  const sign = amount < 0 ? '-' : '';

  // For amounts >= 1 crore (10 million)
  if (absAmount >= 10000000) {
    const crores = (absAmount / 10000000).toFixed(2);
    return `${sign}${symbol}${crores}Cr`;
  }
  
  // For amounts >= 1 lakh (100 thousand)
  if (absAmount >= 100000) {
    const lakhs = (absAmount / 100000).toFixed(2);
    return `${sign}${symbol}${lakhs}L`;
  }
  
  // For smaller amounts, use Indian numeral grouping
  return `${sign}${symbol}${absAmount.toLocaleString('en-IN')}`;
}

/**
 * Format number to Indian currency format with full digits and proper grouping
 * @param amount - The amount to format
 * @param showSymbol - Whether to show ₹ symbol (default: true)
 * @returns Formatted string like ₹1,50,000
 */
export function formatIndianCurrencyFull(amount: number, showSymbol: boolean = true): string {
  const symbol = showSymbol ? '₹' : '';
  const sign = amount < 0 ? '-' : '';
  const absAmount = Math.abs(amount);
  
  return `${sign}${symbol}${absAmount.toLocaleString('en-IN')}`;
}

/**
 * Format date to DD-MM-YYYY format
 * @param date - Date string, Date object, or timestamp
 * @returns Formatted date string like 31-10-2025
 */
export function formatDate(date: string | Date | number): string {
  const d = new Date(date);
  
  // Check if date is valid
  if (isNaN(d.getTime())) {
    return 'Invalid Date';
  }
  
  const day = d.getDate().toString().padStart(2, '0');
  const month = (d.getMonth() + 1).toString().padStart(2, '0');
  const year = d.getFullYear();
  
  return `${day}-${month}-${year}`;
}

/**
 * Format date with time to DD-MM-YYYY HH:mm format
 * @param date - Date string, Date object, or timestamp
 * @returns Formatted date string like 31-10-2025 14:30
 */
export function formatDateTime(date: string | Date | number): string {
  const d = new Date(date);
  
  // Check if date is valid
  if (isNaN(d.getTime())) {
    return 'Invalid Date';
  }
  
  const day = d.getDate().toString().padStart(2, '0');
  const month = (d.getMonth() + 1).toString().padStart(2, '0');
  const year = d.getFullYear();
  const hours = d.getHours().toString().padStart(2, '0');
  const minutes = d.getMinutes().toString().padStart(2, '0');
  
  return `${day}-${month}-${year} ${hours}:${minutes}`;
}

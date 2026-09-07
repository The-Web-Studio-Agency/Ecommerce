'use server';

import { searchApi } from '@/lib/api/search';
import { getAccessToken } from '@/lib/auth/session';

/** The signed-in shopper's recent searches, newest first. Empty for a guest. */
export async function getSearchHistory(): Promise<string[]> {
  const token = await getAccessToken();
  if (!token) return [];

  try {
    return await searchApi.history(token);
  } catch {
    return [];
  }
}

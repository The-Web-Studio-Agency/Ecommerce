export interface CartActionState {
  status: 'idle' | 'success' | 'error';
  message: string | null;
}

export const initialCartState: CartActionState = { status: 'idle', message: null };

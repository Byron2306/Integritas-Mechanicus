export interface RegisteredUser {
  fullName: string;
  username: string;
  accessCode: string;
  registeredAt: number;
  role: 'USER' | 'ADMIN';
}

export const ADMIN_CREDENTIALS = { 
  username: 'ADMIN', 
  accessCode: process.env.ADMIN_ACCESS_CODE || '22807365' 
};

export function isFirstRun(): boolean {
  return !localStorage.getItem('km_registered_user');
}

export function registerUser(user: Omit<RegisteredUser, 'registeredAt' | 'role'>): RegisteredUser {
  const fullUser: RegisteredUser = { ...user, registeredAt: Date.now(), role: 'USER' };
  localStorage.setItem('km_registered_user', JSON.stringify(fullUser));
  return fullUser;
}

export function getRegisteredUser(): RegisteredUser | null {
  const data = localStorage.getItem('km_registered_user');
  return data ? JSON.parse(data) : null;
}

export function validateLogin(username: string, accessCode: string): { valid: boolean; role: 'USER' | 'ADMIN' | null; fullName: string } {
  // ADMIN master route
  if (username === ADMIN_CREDENTIALS.username && accessCode === ADMIN_CREDENTIALS.accessCode) {
    return { valid: true, role: 'ADMIN', fullName: 'MAIN CONTROL ADMINISTRATOR' };
  }
  // Registered user route
  const user = getRegisteredUser();
  if (user && user.username === username && user.accessCode === accessCode) {
    return { valid: true, role: 'USER', fullName: user.fullName };
  }
  return { valid: false, role: null, fullName: '' };
}

export function clearRegistration(): void {
  localStorage.removeItem('km_registered_user');
}

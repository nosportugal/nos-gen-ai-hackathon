import { DOCUMENT } from '@angular/common';
import { Injectable, inject, signal } from '@angular/core';

export type Theme = 'light' | 'dark';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly document = inject(DOCUMENT);
  private readonly selected = signal<Theme>(this.readPreference());
  readonly preference = this.selected.asReadonly();

  constructor() {
    this.apply();
  }

  setPreference(theme: Theme): void {
    this.selected.set(theme);
    try {
      this.document.defaultView!.localStorage.setItem('theme', theme);
    } catch {
      /* Storage may be unavailable. */
    }
    this.apply();
  }

  private readPreference(): Theme {
    try {
      const value = this.document.defaultView!.localStorage.getItem('theme');
      if (value === 'light' || value === 'dark') return value;
    } catch {
      /* Use the default when storage is unavailable. */
    }
    return 'light';
  }

  private apply(): void {
    this.document.documentElement.setAttribute('data-bs-theme', this.preference());
  }
}

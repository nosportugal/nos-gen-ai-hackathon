import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter } from '@angular/router';

import { routes } from './app.routes';
import { DOCUMENT_API_URL } from './document-processor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    // Set to '/api/documents' when the backend is available.
    { provide: DOCUMENT_API_URL, useValue: null },
  ],
};

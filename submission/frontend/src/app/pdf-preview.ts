import { DOCUMENT } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  effect,
  inject,
  input,
  signal,
  viewChild,
} from '@angular/core';
import { faFilePdf } from '@fortawesome/free-solid-svg-icons';
import type { PDFDocumentLoadingTask, RenderTask } from 'pdfjs-dist';
import { LanguageService } from './language.service';

@Component({
  selector: 'app-pdf-preview',
  templateUrl: './pdf-preview.html',
  styleUrl: './pdf-preview.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PdfPreview {
  readonly file = input.required<File>();
  protected readonly language = inject(LanguageService);
  protected readonly icon = faFilePdf;
  protected readonly state = signal<'loading' | 'ready' | 'unavailable'>('loading');
  private readonly document = inject(DOCUMENT);
  private readonly canvas = viewChild<ElementRef<HTMLCanvasElement>>('canvas');

  constructor() {
    effect((onCleanup) => {
      const file = this.file();
      const canvas = this.canvas()?.nativeElement;
      if (!canvas) return;

      let cancelled = false;
      let loading: PDFDocumentLoadingTask | undefined;
      let rendering: RenderTask | undefined;
      const release = () => {
        const task = loading;
        loading = undefined;
        if (task) void task.destroy().catch(() => {});
      };
      onCleanup(() => {
        cancelled = true;
        rendering?.cancel();
        release();
      });
      this.state.set('loading');

      const render = async () => {
        try {
          const [pdf, data] = await Promise.all([import('pdfjs-dist'), file.arrayBuffer()]);
          if (cancelled) return;
          pdf.GlobalWorkerOptions.workerSrc = new URL(
            'pdf.worker.min.mjs',
            this.document.baseURI,
          ).href;
          loading = pdf.getDocument({ data: new Uint8Array(data) });
          const document = await loading.promise;
          if (cancelled) return;
          const page = await document.getPage(1);
          if (cancelled) return;
          const original = page.getViewport({ scale: 1 });
          const scale = Math.min(80 / original.width, 100 / original.height) * 2;
          const viewport = page.getViewport({ scale });
          // Each request renders to its own canvas, so a replacement can never share it.
          const thumbnail = this.document.createElement('canvas');
          thumbnail.width = Math.ceil(viewport.width);
          thumbnail.height = Math.ceil(viewport.height);
          rendering = page.render({ canvas: thumbnail, viewport });
          await rendering.promise;
          if (cancelled) return;
          const context = canvas.getContext('2d');
          if (!context) throw new Error('Canvas is unavailable');
          canvas.width = thumbnail.width;
          canvas.height = thumbnail.height;
          context.drawImage(thumbnail, 0, 0);
          this.state.set('ready');
        } catch {
          if (!cancelled) this.state.set('unavailable');
        } finally {
          release();
        }
      };
      void render();
    });
  }
}

import {
  afterNextRender,
  ChangeDetectionStrategy,
  Component,
  computed,
  ElementRef,
  Injector,
  inject,
  signal,
} from '@angular/core';
import {
  faArrowLeft,
  faArrowRight,
  faFileArrowUp,
  faShieldHalved,
  faXmark,
} from '@fortawesome/free-solid-svg-icons';
import { DocumentService, MIN_ANONYMIZATION_DURATION } from '../../document.service';
import { LanguageService } from '../../language.service';
import { DocumentProgress } from '../../document-progress';
import { Results } from '../results/results';
import { PdfPreview } from '../../pdf-preview';
import { EntitySelection } from '../../entity-selection';
import { categoryDetails } from '../../document-categories';

@Component({
  selector: 'app-anonymize',
  imports: [DocumentProgress, Results, PdfPreview, EntitySelection],
  templateUrl: './anonymize.html',
  styleUrl: './anonymize.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Anonymize {
  protected readonly language = inject(LanguageService);
  protected readonly documents = inject(DocumentService);
  protected readonly fileFormat = computed(
    () => this.documents.file()?.name.split('.').pop()?.toUpperCase() ?? '',
  );
  protected readonly removeIcon = faXmark;
  protected readonly uploadIcon = faFileArrowUp;
  protected readonly nextIcon = faArrowRight;
  protected readonly anonymizationIcon = faShieldHalved;
  protected readonly backIcon = faArrowLeft;
  protected readonly categoryDetails = categoryDetails;
  protected readonly dragging = signal(false);
  protected readonly error = signal<'fileError' | 'emptyPdf' | null>(null);
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly injector = inject(Injector);

  protected choose(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) this.select(Array.from(input.files));
    input.value = '';
  }

  protected dragOver(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(!this.documents.processing());
  }
  protected drop(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(false);
    this.select(Array.from(event.dataTransfer?.files ?? []));
  }
  protected remove(): void {
    this.documents.clear();
    this.error.set(null);
    this.focusHeading();
  }

  protected async startAnalysis(): Promise<void> {
    if (await this.documents.analyze()) this.focusHeading();
  }

  protected async anonymizeSelected(): Promise<void> {
    if (await this.documents.anonymize(MIN_ANONYMIZATION_DURATION)) this.focusHeading();
  }

  protected backToDocument(): void {
    this.documents.returnToDocument();
    this.focusHeading();
  }

  protected backToReview(): void {
    this.documents.returnToReview();
    this.focusHeading();
  }

  private focusHeading(): void {
    afterNextRender(
      () =>
        this.host.nativeElement.querySelector<HTMLElement>('h1')?.focus({ preventScroll: true }),
      { injector: this.injector },
    );
  }

  private select(files: File[]): void {
    if (this.documents.processing()) return;
    const file = files[0];
    if (
      files.length !== 1 ||
      !file ||
      !/\.pdf$/i.test(file.name) ||
      (file.type !== '' && file.type !== 'application/pdf')
    ) {
      this.error.set('fileError');
      return;
    }
    if (!file.size) {
      this.error.set('emptyPdf');
      return;
    }
    this.error.set(null);
    this.documents.select(file);
  }
}

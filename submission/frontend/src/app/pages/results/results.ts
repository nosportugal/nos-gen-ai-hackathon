import { ChangeDetectionStrategy, Component, inject, output } from '@angular/core';
import { DocumentService } from '../../document.service';
import { LanguageService } from '../../language.service';
import { DocumentProgress } from '../../document-progress';
import { faArrowLeft, faDownload } from '@fortawesome/free-solid-svg-icons';
import { categoryDetails } from '../../document-categories';

@Component({
  selector: 'app-results',
  imports: [DocumentProgress],
  templateUrl: './results.html',
  styleUrl: './results.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Results {
  readonly restart = output<void>();
  readonly back = output<void>();
  protected readonly language = inject(LanguageService);
  protected readonly documents = inject(DocumentService);
  protected readonly downloadIcon = faDownload;
  protected readonly backIcon = faArrowLeft;
  protected readonly categoryDetails = categoryDetails;

  protected download(): void {
    const result = this.documents.result();
    if (!result) return;
    const url = URL.createObjectURL(result.download.blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = result.download.name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  protected backToReview(): void {
    this.back.emit();
  }
}

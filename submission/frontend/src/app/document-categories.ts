import {
  IconDefinition,
  faAddressBook,
  faBriefcase,
  faCakeCandles,
  faCalendarDay,
  faCreditCard,
  faFingerprint,
  faHeartPulse,
  faHouseUser,
  faIdCard,
  faTag,
  faUser,
  faUserDoctor,
  faVenusMars,
} from '@fortawesome/free-solid-svg-icons';

export type CategoryLabelKey =
  | 'categoryName'
  | 'categoryId'
  | 'categoryContact'
  | 'categoryDob'
  | 'categoryFinancial'
  | 'categoryHealth'
  | 'categorySpecial'
  | 'categoryPrivateLife'
  | 'categoryAge'
  | 'categoryOccupation'
  | 'categoryClinician'
  | 'categorySex'
  | 'categoryOther';

export interface CategoryDetails {
  readonly labelKey: CategoryLabelKey;
  readonly icon: IconDefinition;
  readonly color: string;
}

export const CATEGORY_DETAILS = {
  NAME: { labelKey: 'categoryName', icon: faUser, color: 'var(--category-name)' },
  ID: { labelKey: 'categoryId', icon: faIdCard, color: 'var(--category-id)' },
  CONTACT: {
    labelKey: 'categoryContact',
    icon: faAddressBook,
    color: 'var(--category-contact)',
  },
  DOB: { labelKey: 'categoryDob', icon: faCalendarDay, color: 'var(--category-dob)' },
  FINANCIAL: {
    labelKey: 'categoryFinancial',
    icon: faCreditCard,
    color: 'var(--category-financial)',
  },
  HEALTH: { labelKey: 'categoryHealth', icon: faHeartPulse, color: 'var(--category-health)' },
  SPECIAL: {
    labelKey: 'categorySpecial',
    icon: faFingerprint,
    color: 'var(--category-special)',
  },
  PRIVATE_LIFE: {
    labelKey: 'categoryPrivateLife',
    icon: faHouseUser,
    color: 'var(--category-private-life)',
  },
  AGE: { labelKey: 'categoryAge', icon: faCakeCandles, color: 'var(--category-age)' },
  OCCUPATION: {
    labelKey: 'categoryOccupation',
    icon: faBriefcase,
    color: 'var(--category-occupation)',
  },
  CLINICIAN: {
    labelKey: 'categoryClinician',
    icon: faUserDoctor,
    color: 'var(--category-clinician)',
  },
  SEX: { labelKey: 'categorySex', icon: faVenusMars, color: 'var(--category-sex)' },
} as const satisfies Record<string, CategoryDetails>;

const other: CategoryDetails = {
  labelKey: 'categoryOther',
  icon: faTag,
  color: 'var(--muted)',
};

export function categoryDetails(type: string): CategoryDetails {
  return Object.prototype.hasOwnProperty.call(CATEGORY_DETAILS, type)
    ? CATEGORY_DETAILS[type as keyof typeof CATEGORY_DETAILS]
    : other;
}

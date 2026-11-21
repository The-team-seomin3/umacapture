/// Build-time identity shared with the Windows package configuration.
const bool isKoreanFactorApp = String.fromEnvironment('UMACAPTURE_VARIANT', defaultValue: 'jp') == 'kr';

const String applicationTitle = isKoreanFactorApp ? 'umacapture KR · 한국어 인자 OCR' : 'umacapture';
const String koreanWindowTitle = 'umacapture (Korean Factor OCR)';

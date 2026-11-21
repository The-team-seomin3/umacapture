// The Korean workflow is a local Windows application. Keep its process/filesystem
// and Image.file UI out of the existing web build.
export 'kr_factor_workflow_io.dart' if (dart.library.js_interop) 'kr_factor_workflow_web.dart';

// HistoScroll deployment configuration.
// The Supabase publishable/anon key is designed to be used in browser apps.
// Security is enforced by the Row Level Security policies in supabase/setup.sql.
export const config = {
  SUPABASE_URL: 'https://hxxgqykttejomizbqdlp.supabase.co',
  SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_yfdfi6Wwy3_N4n5F4l3_Jw_k-YeVNxG',
  BOOK_BUCKET: 'book-packages',

  // Optional. Leave empty until the Raspberry Pi media service is deployed.
  // Example: 'https://media.example.de'
  PI_MEDIA_BASE_URL: '',
};

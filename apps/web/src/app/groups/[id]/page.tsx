import GroupView from "@/components/GroupView";

export default async function GroupPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <GroupView groupId={id} />;
}
